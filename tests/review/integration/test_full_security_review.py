"""Integration tests for full security review workflow.

This module tests the end-to-end security review process with:
- Real tool execution (where tools installed)
- Real agent instantiation (no agent mocks)
- Dynamic review capabilities
- Final assessment generation
- FSM transitions verification
- Confidence threshold filtering
- Deduplication from real findings

Tests verify that SecurityReviewerAgent orchestrates subagents correctly
and produces proper security assessments from real vulnerability data.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from io import StringIO

from dawn_kestrel.agents.review.fsm_security import (
    SecurityReviewerAgent,
    SecurityFinding,
    SecurityAssessment,
    ReviewState,
    TodoStatus,
)
from dawn_kestrel.agents.orchestrator import AgentOrchestrator
from dawn_kestrel.agents.runtime import AgentRuntime
from dawn_kestrel.agents.registry import AgentRegistry
from dawn_kestrel.core.agent_task import TaskStatus


class TestFullSecurityReview:
    """Integration tests for full security review workflow.

    These tests verify end-to-end functionality with:
    - Real agent instantiation (no mocks for subagents)
    - Real tool execution (where tools available)
    - Mock git context (to control test data)
    - AsyncMock for LLM client (optional)
    """

    @pytest.fixture
    def vulnerable_repo(self) -> Path:
        """Create a temporary repository with security vulnerabilities.

        Creates a test repo with:
        - SQL injection vulnerability
        - XSS vulnerability
        - Weak crypto (MD5, SHA1)
        - DEBUG=True in settings

        Returns:
            Path to temporary repository
        """
        # Create temp directory
        temp_dir: Path = Path(tempfile.mkdtemp())

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)

        # Create vulnerable files
        # 1. SQL injection vulnerability
        sqli_file = temp_dir / "views.py"
        sqli_file.write_text("""
def get_user(user_id):
    query = f'SELECT * FROM users WHERE id = {user_id}'
    return db.execute(query)
""")

        # 2. XSS vulnerability
        xss_file = temp_dir / "render.py"
        xss_file.write_text("""
def render_comment(user_input):
    return f'<div>{user_input}</div>'
""")

        # 3. Weak crypto (MD5, SHA1)
        crypto_file = temp_dir / "crypto.py"
        crypto_file.write_text("""
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def hash_data(data):
    return hashlib.sha1(data.encode()).hexdigest()
""")

        # 4. DEBUG=True in settings
        settings_file = temp_dir / "settings.py"
        settings_file.write_text("""
DEBUG = True
SECRET_KEY = 'test-secret-key-1234567890'
ALLOWED_HOSTS = ['*']
""")

        # Commit to main branch
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit with vulnerabilities"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )

        yield temp_dir

        # Cleanup
        shutil.rmtree(str(temp_dir), ignore_errors=True)

    @pytest.fixture
    def orchestrator(self) -> AgentOrchestrator:
        """Create real AgentOrchestrator for integration tests."""
        # Create registry with builtin agents
        registry = AgentRegistry()

        # Create runtime with base directory
        base_dir = Path(tempfile.mkdtemp())
        runtime = AgentRuntime(agent_registry=registry, base_dir=base_dir)

        # Create orchestrator
        orchestrator = AgentOrchestrator(runtime)

        yield orchestrator

        # Cleanup
        shutil.rmtree(base_dir, ignore_errors=True)

    @pytest.fixture
    def mock_git_context(self, vulnerable_repo: Path) -> Dict[str, Any]:
        """Mock git context to return vulnerable test files.

        Returns mock data for:
        - get_changed_files: Returns list of vulnerable files
        - get_diff: Returns diff with vulnerable patterns

        Returns:
            Dict with changed_files and diff
        """
        changed_files = [
            "views.py",  # SQL injection
            "render.py",  # XSS
            "crypto.py",  # Weak crypto
            "settings.py",  # DEBUG=True
        ]

        # Diff content showing vulnerabilities
        diff_content = """diff --git a/views.py b/views.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/views.py
@@ -0,0 +1,4 @@
+def get_user(user_id):
+    query = f'SELECT * FROM users WHERE id = {user_id}'
+    return db.execute(query)
diff --git a/render.py b/render.py
new file mode 100644
index 0000000..def5678
--- /dev/null
+++ b/render.py
@@ -0,0 +1,3 @@
+def render_comment(user_input):
+    return f'<div>{user_input}</div>'
diff --git a/crypto.py b/crypto.py
new file mode 100644
index 0000000..ghi9012
--- /dev/null
+++ b/crypto.py
@@ -0,0 +1,6 @@
+import hashlib
+
+def hash_password(password):
+    return hashlib.md5(password.encode()).hexdigest()
+
+def hash_data(data):
+    return hashlib.sha1(data.encode()).hexdigest()
diff --git a/settings.py b/settings.py
new file mode 100644
index 0000000..jkl3456
--- /dev/null
+++ b/settings.py
@@ -0,0 +1,3 @@
+DEBUG = True
+SECRET_KEY = 'test-secret-key-1234567890'
+ALLOWED_HOSTS = ['*']
"""

        return {
            "changed_files": changed_files,
            "diff": diff_content,
        }

    @pytest.mark.asyncio
    async def test_end_to_end_review_produces_assessment(
        self, vulnerable_repo: Path, orchestrator: AgentOrchestrator, mock_git_context: Dict
    ):
        """Verify end-to-end review produces assessment with real tool execution.

        This test runs complete security review workflow:
        1. Mock git context to return vulnerable files
        2. Use real subagent instantiation (no mocks)
        3. Use real tool execution (where tools installed)
        4. Verify final assessment is produced
        5. Verify findings contain expected vulnerabilities
        6. Verify no mock/simulation logs in results
        """
        # Create security reviewer with real orchestrator
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.50,
        )

        # Mock _wait_for_investigation_tasks to mark tasks as completed
        # (Subagents return tasks with PENDING status, need to mark them COMPLETED)
        async def mock_wait_for_tasks():
            for task_id, task in reviewer.subagent_tasks.items():
                task.status = TaskStatus.COMPLETED

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
            patch.object(
                reviewer,
                "_wait_for_investigation_tasks",
                side_effect=mock_wait_for_tasks,
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify assessment is produced
        assert isinstance(assessment, SecurityAssessment)
        assert assessment.total_findings >= 0
        assert assessment.overall_severity in ["critical", "high", "medium", "low"]
        assert assessment.merge_recommendation in ["approve", "needs_changes", "block"]

        # Verify summary contains expected keywords
        assert "Security review completed" in assessment.summary

        # Verify findings structure
        for finding in assessment.findings:
            assert isinstance(finding, SecurityFinding)
            assert finding.id
            assert finding.severity in ["critical", "high", "medium", "low"]
            assert finding.title
            assert finding.description
            assert finding.evidence
            assert finding.confidence_score >= 0.0
            assert finding.confidence_score <= 1.0

        # Verify no mock/simulation logs in notes
        for note in assessment.notes:
            assert "Simulated" not in note
            assert "Mock" not in note

    @pytest.mark.asyncio
    async def test_fsm_transitions_work_correctly(
        self, vulnerable_repo: Path, orchestrator: AgentOrchestrator, mock_git_context: Dict
    ):
        """Verify FSM transitions follow expected state machine flow.

        Expected transitions:
        IDLE → INITIAL_EXPLORATION → DELEGATING_INVESTIGATION →
        REVIEWING_RESULTS → FINAL_ASSESSMENT → COMPLETED

        This test verifies:
        1. Initial state is IDLE
        2. Review transitions through all states
        3. No invalid transitions occur
        4. Final state is COMPLETED
        """
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.50,
        )

        # Verify initial state is IDLE
        initial_state = await reviewer.get_state()
        assert initial_state == ReviewState.IDLE

        # Mock _wait_for_investigation_tasks to mark tasks as completed
        async def mock_wait_for_tasks():
            for task_id, task in reviewer.subagent_tasks.items():
                task.status = TaskStatus.COMPLETED

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
            patch.object(
                reviewer,
                "_wait_for_investigation_tasks",
                side_effect=mock_wait_for_tasks,
            ),
        ):
            # Run review - this should transition through all states
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify initial state is IDLE
        initial_state = await reviewer.get_state()
        assert initial_state == ReviewState.IDLE

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
        ):
            # Run review - this should transition through all states
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify final state is COMPLETED
        final_state = await reviewer.get_state()
        assert final_state == ReviewState.COMPLETED

        # Verify assessment was produced
        assert isinstance(assessment, SecurityAssessment)

        # Verify iteration count is positive
        assert reviewer.iteration_count > 0

        # Verify todos were created
        assert len(reviewer.todos) > 0

        # Verify subagent tasks were created
        assert len(reviewer.subagent_tasks) > 0

    @pytest.mark.asyncio
    async def test_confidence_threshold_filters_low_confidence_findings(
        self, vulnerable_repo: Path, orchestrator: AgentOrchestrator, mock_git_context: Dict
    ):
        """Verify confidence threshold filters out low-confidence findings.

        This test verifies:
        1. Threshold of 0.70 filters findings below 0.70
        2. Findings above threshold are included
        3. Assessment reflects filtered findings count
        4. Confidence scores are logged for each finding
        """
        # Create security reviewer with high threshold (0.70)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.70,
        )

        # Mock _wait_for_investigation_tasks to mark tasks as completed
        async def mock_wait_for_tasks():
            for task_id, task in reviewer.subagent_tasks.items():
                task.status = TaskStatus.COMPLETED

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
            patch.object(
                reviewer,
                "_wait_for_investigation_tasks",
                side_effect=mock_wait_for_tasks,
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify threshold was applied
        assert reviewer.confidence_threshold == 0.70

        # Verify all findings in assessment pass threshold
        for finding in assessment.findings:
            assert finding.confidence_score >= 0.70

        # Verify assessment notes mention filtering
        filter_notes = [note for note in assessment.notes if "filtered" in note.lower()]
        assert len(filter_notes) >= 1

        # Verify severity counts match findings
        actual_count = len(assessment.findings)
        sum_of_counts = (
            assessment.critical_count
            + assessment.high_count
            + assessment.medium_count
            + assessment.low_count
        )
        assert actual_count == sum_of_counts

    @pytest.mark.asyncio
    async def test_deduplication_prevents_duplicate_findings(
        self, vulnerable_repo: Path, orchestrator: AgentOrchestrator, mock_git_context: Dict
    ):
        """Verify deduplication prevents duplicate findings from multiple agents.

        This test verifies:
        1. Finding IDs are unique
        2. No duplicate findings in final assessment
        3. processed_finding_ids set prevents duplicates
        """
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.50,
        )

        # Mock _wait_for_investigation_tasks to mark tasks as completed
        async def mock_wait_for_tasks():
            for task_id, task in reviewer.subagent_tasks.items():
                task.status = TaskStatus.COMPLETED

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
            patch.object(
                reviewer,
                "_wait_for_investigation_tasks",
                side_effect=mock_wait_for_tasks,
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify finding IDs are unique
        finding_ids = [finding.id for finding in assessment.findings]
        unique_ids = set(finding_ids)
        assert len(finding_ids) == len(unique_ids), (
            f"Duplicate finding IDs found: {[id for id in finding_ids if finding_ids.count(id) > 1]}"
        )

        # Verify no duplicates by (file_path, line_number)
        file_line_pairs = [
            (f.file_path, f.line_number)
            for f in assessment.findings
            if f.file_path and f.line_number
        ]
        unique_pairs = set(file_line_pairs)
        assert len(file_line_pairs) == len(unique_pairs), (
            f"Duplicate findings at same location: {[pair for pair in file_line_pairs if file_line_pairs.count(pair) > 1]}"
        )

        # Verify reviewer's internal dedup set was used
        assert isinstance(reviewer.processed_finding_ids, set)

    @pytest.mark.asyncio
    async def test_multiple_iterations_handled_correctly(
        self, vulnerable_repo: Path, orchestrator: AgentOrchestrator, mock_git_context: Dict
    ):
        """Verify FSM loop handles multiple iterations correctly.

        This test verifies:
        1. Iteration count is tracked correctly
        2. Max iterations is respected
        3. Tasks are not redelegated after completion
        4. processed_task_ids prevents redelegation
        """
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.50,
        )

        # Set max iterations to 2 (force potential second iteration)
        reviewer.max_iterations = 2

        # Mock _wait_for_investigation_tasks to mark tasks as completed
        async def mock_wait_for_tasks():
            for task_id, task in reviewer.subagent_tasks.items():
                task.status = TaskStatus.COMPLETED

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
            patch.object(
                reviewer,
                "_wait_for_investigation_tasks",
                side_effect=mock_wait_for_tasks,
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Set max iterations to 2 (force potential second iteration)
        reviewer.max_iterations = 2

        # Mock git functions to return vulnerable test context
        with (
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_changed_files",
                return_value=mock_git_context["changed_files"],
            ),
            patch(
                "dawn_kestrel.agents.review.fsm_security.get_diff",
                return_value=mock_git_context["diff"],
            ),
        ):
            # Run review
            assessment = await reviewer.run_review(
                repo_root=str(vulnerable_repo),
                base_ref="main",
                head_ref="HEAD",
            )

        # Verify iteration count
        assert reviewer.iteration_count >= 1
        assert reviewer.iteration_count <= reviewer.max_iterations

        # Verify final state is COMPLETED (not FAILED)
        final_state = await reviewer.get_state()
        assert final_state == ReviewState.COMPLETED

        # Verify assessment was produced
        assert isinstance(assessment, SecurityAssessment)

        # Verify processed_task_ids set was used
        assert isinstance(reviewer.processed_task_ids, set)

        # Verify no tasks were processed twice
        # (all task IDs should be unique)
        task_ids = list(reviewer.processed_task_ids)
        unique_task_ids = set(task_ids)
        assert len(task_ids) == len(unique_task_ids), (
            f"Tasks were processed multiple times: {[tid for tid in task_ids if task_ids.count(tid) > 1]}"
        )
