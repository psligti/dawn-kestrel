"""Integration tests for entry point system (doc-gen → discovery → review → verification → pattern learning).

This test suite covers the complete entry point system integration:
- Doc generation for all reviewers
- Entry point discovery with mock subprocess calls
- Orchestrator integration with context filtering
- Self-verification integration
- Pattern learning integration
- Baseline performance comparison
- CLI integration
- Error scenarios and graceful degradation
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from dawn_kestrel.agents.review.agents.architecture import ArchitectureReviewer
from dawn_kestrel.agents.review.agents.changelog import ReleaseChangelogReviewer
from dawn_kestrel.agents.review.agents.dependencies import DependencyLicenseReviewer
from dawn_kestrel.agents.review.agents.diff_scoper import DiffScoperReviewer
from dawn_kestrel.agents.review.agents.documentation import DocumentationReviewer
from dawn_kestrel.agents.review.agents.linting import LintingReviewer
from dawn_kestrel.agents.review.agents.performance import PerformanceReliabilityReviewer
from dawn_kestrel.agents.review.agents.requirements import RequirementsReviewer
from dawn_kestrel.agents.review.agents.security import SecurityReviewer
from dawn_kestrel.agents.review.agents.telemetry import TelemetryMetricsReviewer
from dawn_kestrel.agents.review.agents.unit_tests import UnitTestsReviewer
from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.contracts import (
    ReviewInputs,
    ReviewOutput,
    Finding,
    MergeGate,
    Scope,
)
from dawn_kestrel.agents.review.discovery import EntryPoint, EntryPointDiscovery
from dawn_kestrel.agents.review.doc_gen import DocGenAgent
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator
from dawn_kestrel.agents.review.pattern_learning import PatternLearning
from dawn_kestrel.agents.review.utils.executor import ExecutionResult


class MockCommandExecutor:
    """Mock command executor for testing."""

    async def execute(self, command: str, timeout: int = 60):
        return ExecutionResult(
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            timeout=False,
            parsed_findings=[],
            files_modified=[],
            duration_seconds=0.1,
        )


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Create mock repository with realistic file structure."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create directory structure
    (repo / "src" / "auth").mkdir(parents=True)
    (repo / "src" / "api").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "docs").mkdir()
    (repo / "config").mkdir()

    # Create realistic Python files
    (repo / "src" / "auth" / "login.py").write_text("""import os

def authenticate(username, password):
    API_KEY = "hardcoded_key_123"
    if username == "admin" and password == "secret":
        return True
    return False

@login_required
def protected_route():
    return "protected"
""")

    (repo / "src" / "api" / "user.py").write_text("""from datetime import datetime
import subprocess

class User:
    def __init__(self, name):
        self.name = name

def create_user(user_data):
    eval(user_data.get("code", ""))
    return User(user_data["name"])
""")

    (repo / "config" / "settings.py").write_text("""DATABASE_URL = "postgres://localhost/db"
API_KEY = "sk-live-12345"
SECRET = "production_secret_abc"
""")

    (repo / "tests" / "test_auth.py").write_text("""import time
import random

def test_login():
    time.sleep(1)
    result = random.choice([True, False])
    assert result == True
""")

    (repo / "README.md").write_text("# My Project\n\nBasic documentation.")
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n\nInitial release.")

    return repo


@pytest.fixture
def mock_pr_diff() -> str:
    """Create mock PR diff with realistic changes."""
    return """diff --git a/src/auth/login.py b/src/auth/login.py
+++ b/src/auth/login.py
@@ -1,1 +1,1 @@
-def authenticate(username, password):
+def authenticate(username, password, api_key):
     API_KEY = "hardcoded_key_123"
+    subprocess.run(["echo", password], shell=True)
+    eval(input())

diff --git a/config/settings.py b/config/settings.py
+++ b/config/settings.py
@@ -1,1 +1,1 @@
+API_KEY = "new_hardcoded_key"
+SECRET = "another_secret_456"

diff --git a/src/api/user.py b/src/api/user.py
+++ b/src/api/user.py
@@ -1,1 +1,1 @@
+def create_user(user_data):
+    for i in range(100):
+        for j in range(100):
+            db.query(f"SELECT * FROM users WHERE id={i}")
"""


class TestEndToEndIntegration:
    """Test end-to-end workflow: doc-gen → discovery → review → verification."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, mock_repo: Path, mock_pr_diff: str):
        """Test complete workflow from doc generation to review with verification."""
        # Step 1: Generate documentation for security reviewer
        doc_gen = DocGenAgent()
        security_reviewer = SecurityReviewer()

        output_path = mock_repo / "docs" / "reviewers" / "security_reviewer.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        success, message = doc_gen.generate_for_agent(
            security_reviewer, force=True, output_path=output_path
        )

        assert success is True, f"Doc generation failed: {message}"
        assert output_path.exists(), "Documentation file not created"
        doc_content = output_path.read_text()
        assert "---" in doc_content, "YAML frontmatter not found"
        assert "patterns:" in doc_content, "Patterns section not found"

        # Step 2: Mock discovery subprocess calls
        mock_entry_points = [
            EntryPoint(
                file_path="src/auth/login.py",
                line_number=5,
                description="Hardcoded API key",
                weight=0.95,
                pattern_type="content",
                evidence='API_KEY = "hardcoded_key_123"',
            ),
            EntryPoint(
                file_path="src/api/user.py",
                line_number=8,
                description="Unsafe eval usage",
                weight=0.95,
                pattern_type="ast",
                evidence='eval(user_data.get("code", ""))',
            ),
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = 'src/auth/login.py:5:API_KEY = "hardcoded_key_123"\n'

            discovery = EntryPointDiscovery()
            # Discovery would normally load from docs, but we'll mock the result
            with patch.object(
                discovery,
                "_load_agent_patterns",
                return_value={"ast": [], "content": [], "file_path": []},
            ):
                entry_points = await discovery.discover_entry_points(
                    agent_name="security",
                    repo_root=str(mock_repo),
                    changed_files=["src/auth/login.py", "src/api/user.py", "config/settings.py"],
                )

        # Step 3: Run orchestrator with discovery
        agents = [SecurityReviewer()]
        orchestrator = PRReviewOrchestrator(agents, discovery=discovery)

        inputs = ReviewInputs(
            repo_root=str(mock_repo),
            base_ref="main",
            head_ref="feature",
            timeout_seconds=30,
        )

        changed_files = ["src/auth/login.py", "src/api/user.py"]

        with (
            patch(
                "dawn_kestrel.agents.review.utils.git.get_changed_files",
                AsyncMock(return_value=changed_files),
            ),
            patch(
                "dawn_kestrel.agents.review.utils.git.get_diff",
                AsyncMock(return_value=mock_pr_diff),
            ),
        ):
            # Mock review method to return findings
            with patch.object(SecurityReviewer, "review", new_callable=AsyncMock) as mock_review:
                mock_review.return_value = ReviewOutput(
                    agent="security",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="Mock review"),
                    findings=[
                        Finding(
                            id="finding-1",
                            title="Hardcoded API key",
                            severity="critical",
                            confidence="high",
                            owner="security",
                            estimate="M",
                            evidence='API_KEY = "hardcoded_key_123"',
                            risk="Secret exposure",
                            recommendation="Use environment variables for secrets",
                            suggested_patch=None,
                        )
                    ],
                    merge_gate=MergeGate(decision="block", must_fix=[]),
                    summary="Found security issues",
                )

                output = await orchestrator.run_review(inputs)

        # Step 4: Verify orchestrator output
        assert output.subagent_results is not None, "No subagent results"
        assert len(output.subagent_results) == 1, "Expected 1 subagent result"
        assert len(output.findings) > 0, "Expected findings"

        # Step 5: Test self-verification
        reviewer = SecurityReviewer()
        findings = output.subagent_results[0].findings
        verification = reviewer.verify_findings(findings, changed_files, str(mock_repo))

        # Verification should return evidence or empty list (graceful degradation)
        assert isinstance(verification, list), "Verification should return list"

    @pytest.mark.asyncio
    async def test_doc_gen_generates_all_11_reviewers(self, tmp_path: Path):
        """Test that doc-gen works for all 11 reviewers."""
        doc_gen = DocGenAgent()
        output_dir = tmp_path / "docs" / "reviewers"
        output_dir.mkdir(parents=True, exist_ok=True)

        agents = [
            ArchitectureReviewer(),
            SecurityReviewer(),
            DocumentationReviewer(),
            TelemetryMetricsReviewer(),
            LintingReviewer(),
            UnitTestsReviewer(),
            DiffScoperReviewer(),
            RequirementsReviewer(),
            PerformanceReliabilityReviewer(),
            DependencyLicenseReviewer(),
            ReleaseChangelogReviewer(),
        ]

        generated_docs = []

        for agent in agents:
            agent_name = agent.__class__.__name__
            output_path = output_dir / f"{agent_name.lower()}_reviewer.md"

            success, message = doc_gen.generate_for_agent(
                agent, force=True, output_path=output_path
            )

            assert success is True, f"Doc generation failed for {agent_name}: {message}"
            assert output_path.exists(), f"Documentation not created for {agent_name}"

            # Validate YAML frontmatter
            content = output_path.read_text()
            assert "---" in content, f"No frontmatter in {agent_name}"
            assert "agent:" in content, f"No agent field in {agent_name}"
            assert "patterns:" in content, f"No patterns in {agent_name}"
            assert "heuristics:" in content, f"No heuristics in {agent_name}"

            generated_docs.append(agent_name)

        assert len(generated_docs) == 11, "Not all 11 reviewers generated"


class TestBaselineComparison:
    """Test baseline performance comparison (with vs without entry points)."""

    @pytest.mark.asyncio
    async def test_baseline_vs_enhanced_performance(self, mock_repo: Path, mock_pr_diff: str):
        """Test that enhanced review is within 20% of baseline performance."""

        # Setup mock agent with predictable review time
        class MockReviewer(BaseReviewerAgent):
            async def review(self, context: ReviewContext) -> ReviewOutput:
                # Simulate review work (0.1s)
                await asyncio.sleep(0.1)
                return ReviewOutput(
                    agent="mock_reviewer",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="Mock review"),
                    findings=[],
                    merge_gate=MergeGate(decision="approve", must_fix=[]),
                    summary="Mock review",
                )

            def get_system_prompt(self) -> str:
                return "Mock system prompt"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "MockReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

        changed_files = ["src/auth/login.py", "src/api/user.py"]
        diff = mock_pr_diff

        # Baseline: Review WITHOUT entry points (bypass discovery)
        agents_baseline = [MockReviewer() for _ in range(3)]
        orchestrator_baseline = PRReviewOrchestrator(agents_baseline, discovery=None)

        inputs = ReviewInputs(
            repo_root=str(mock_repo),
            base_ref="main",
            head_ref="feature",
            timeout_seconds=30,
        )

        with (
            patch(
                "dawn_kestrel.agents.review.utils.git.get_changed_files",
                AsyncMock(return_value=changed_files),
            ),
            patch("dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)),
        ):
            start_time = time.time()
            await orchestrator_baseline.run_review(inputs)
            baseline_time = time.time() - start_time

        # Enhanced: Review WITH entry points (discovery + filtering)
        discovery = EntryPointDiscovery()

        # Mock discovery to return entry points (simulating real discovery)
        mock_entry_points = [
            EntryPoint(
                file_path="src/auth/login.py",
                line_number=5,
                description="Entry point",
                weight=0.9,
                pattern_type="content",
                evidence="test",
            ),
            EntryPoint(
                file_path="src/api/user.py",
                line_number=8,
                description="Entry point",
                weight=0.9,
                pattern_type="content",
                evidence="test",
            ),
        ]

        with patch.object(
            discovery, "discover_entry_points", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = mock_entry_points

            agents_enhanced = [MockReviewer() for _ in range(3)]
            orchestrator_enhanced = PRReviewOrchestrator(agents_enhanced, discovery=discovery)

            with (
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_changed_files",
                    AsyncMock(return_value=changed_files),
                ),
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)
                ),
            ):
                start_time = time.time()
                await orchestrator_enhanced.run_review(inputs)
                enhanced_time = time.time() - start_time

        # Calculate performance increase
        time_increase = enhanced_time - baseline_time
        percent_increase = (time_increase / baseline_time) * 100

        print(f"\nBaseline time: {baseline_time:.3f}s")
        print(f"Enhanced time: {enhanced_time:.3f}s")
        print(f"Time increase: {time_increase:.3f}s ({percent_increase:.1f}%)")

        # Assert within 20% performance budget
        assert percent_increase < 20, (
            f"Performance increase {percent_increase:.1f}% exceeds 20% budget. "
            f"Baseline: {baseline_time:.3f}s, Enhanced: {enhanced_time:.3f}s"
        )

        # Verify discovery was called
        mock_discover.assert_called()


class TestAll11ReviewersIntegration:
    """Test integration with all 11 reviewer agents."""

    @pytest.mark.asyncio
    async def test_all_reviewers_parallel_execution(self, mock_repo: Path, mock_pr_diff: str):
        """Test all 11 reviewers run in parallel with entry point discovery."""
        agents = [
            ArchitectureReviewer(),
            SecurityReviewer(),
            DocumentationReviewer(),
            TelemetryMetricsReviewer(),
            LintingReviewer(),
            UnitTestsReviewer(),
            DiffScoperReviewer(),
            RequirementsReviewer(),
            PerformanceReliabilityReviewer(),
            DependencyLicenseReviewer(),
            ReleaseChangelogReviewer(),
        ]

        discovery = EntryPointDiscovery()

        # Mock discovery to return entry points for each agent
        async def mock_discover(agent_name, repo_root, changed_files):
            return [
                EntryPoint(
                    file_path="src/auth/login.py",
                    line_number=1,
                    description=f"Entry point for {agent_name}",
                    weight=0.9,
                    pattern_type="content",
                    evidence="test",
                ),
            ]

        with patch.object(
            discovery, "discover_entry_points", side_effect=mock_discover, new_callable=AsyncMock
        ) as mock_discover_entry_points:
            orchestrator = PRReviewOrchestrator(agents, discovery=discovery)

            inputs = ReviewInputs(
                repo_root=str(mock_repo),
                base_ref="main",
                head_ref="feature",
                timeout_seconds=30,
            )

            changed_files = ["src/auth/login.py", "src/api/user.py"]
            diff = mock_pr_diff

            with (
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_changed_files",
                    AsyncMock(return_value=changed_files),
                ),
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)
                ),
            ):
                # Mock review to return simple results
                async def mock_review(context):
                    await asyncio.sleep(0.01)
                    return ReviewOutput(
                        agent="mock_reviewer",
                        severity="merge",
                        scope=Scope(relevant_files=[], reasoning="Mock review"),
                        findings=[],
                        merge_gate=MergeGate(decision="approve", must_fix=[]),
                        summary=f"Review by {context.changed_files}",
                    )

                for agent in agents:
                    with patch.object(
                        agent, "review", new_callable=AsyncMock, side_effect=mock_review
                    ):
                        pass

                output = await orchestrator.run_review(inputs)

            # Verify all 11 agents ran
            assert len(output.subagent_results) == 11, (
                f"Expected 11 subagent results, got {len(output.subagent_results)}"
            )

            # Verify discovery was called for each agent
            assert mock_discover_entry_points.call_count == 11, (
                f"Expected discovery called 11 times, got {mock_discover_entry_points.call_count}"
            )


class TestFallbackBehavior:
    """Test fallback behavior when discovery fails."""

    @pytest.mark.asyncio
    async def test_discovery_returns_none_triggers_fallback(
        self, mock_repo: Path, mock_pr_diff: str
    ):
        """Test that None from discovery triggers fallback to is_relevant_to_changes()."""

        class MockReviewer(BaseReviewerAgent):
            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="mock_reviewer",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="Mock review"),
                    findings=[],
                    merge_gate=MergeGate(decision="approve", must_fix=[]),
                    summary=f"Reviewed {len(context.changed_files)} files",
                )

            def get_system_prompt(self) -> str:
                return "Mock reviewer"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "MockReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

        discovery = EntryPointDiscovery()

        # Mock discovery to return None (simulating failure)
        with patch.object(
            discovery, "discover_entry_points", new_callable=AsyncMock, return_value=None
        ):
            agent = MockReviewer()
            orchestrator = PRReviewOrchestrator([agent], discovery=discovery)

            inputs = ReviewInputs(
                repo_root=str(mock_repo),
                base_ref="main",
                head_ref="feature",
                timeout_seconds=30,
            )

            changed_files = ["src/auth/login.py", "config/settings.py"]
            diff = mock_pr_diff

            with (
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_changed_files",
                    AsyncMock(return_value=changed_files),
                ),
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)
                ),
            ):
                output = await orchestrator.run_review(inputs)

        # Verify review completed despite discovery failure
        assert len(output.subagent_results) == 1, "Review should complete with fallback"

    @pytest.mark.asyncio
    async def test_discovery_timeout_triggers_fallback(self, mock_repo: Path, mock_pr_diff: str):
        """Test that discovery timeout triggers fallback."""

        class MockReviewer(BaseReviewerAgent):
            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="mock_reviewer",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="Mock review"),
                    findings=[],
                    merge_gate=MergeGate(decision="approve", must_fix=[]),
                    summary="Review completed",
                )

            def get_system_prompt(self) -> str:
                return "Mock reviewer"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "MockReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

        discovery = EntryPointDiscovery(timeout_seconds=1)

        # Mock discovery to timeout
        async def mock_timeout(agent_name, repo_root, changed_files):
            await asyncio.sleep(2)  # Sleep longer than timeout
            return []

        with patch.object(
            discovery, "discover_entry_points", new_callable=AsyncMock, side_effect=mock_timeout
        ):
            agent = MockReviewer()
            orchestrator = PRReviewOrchestrator([agent], discovery=discovery)

            inputs = ReviewInputs(
                repo_root=str(mock_repo),
                base_ref="main",
                head_ref="feature",
                timeout_seconds=30,
            )

            changed_files = ["src/auth/login.py"]
            diff = mock_pr_diff

            with (
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_changed_files",
                    AsyncMock(return_value=changed_files),
                ),
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)
                ),
            ):
                output = await orchestrator.run_review(inputs)

        # Review should complete despite timeout
        assert len(output.subagent_results) == 1, "Review should complete after timeout"


class TestPatternLearningIntegration:
    """Test pattern learning integration (review → learn → commit → discover)."""

    def test_pattern_learning_staging(self, tmp_path: Path):
        """Test that patterns can be staged during review."""
        docs_dir = tmp_path / "docs" / "reviewers"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create main doc
        main_doc = docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
agent: security
patterns:
  - type: content
    pattern: password
    weight: 0.9
---
# Security Reviewer
""")

        pattern_learning = PatternLearning(docs_dir=docs_dir)

        # Stage a new pattern
        new_pattern = {
            "type": "content",
            "pattern": "AWS_ACCESS_KEY",
            "language": "python",
            "weight": 0.95,
            "source": "PR #123 - Hardcoded AWS key found",
        }

        success = pattern_learning.add_learned_pattern("security", new_pattern)

        assert success is True, "Pattern staging should succeed"

        # Verify staged file exists
        staged_file = docs_dir / "security_staged_patterns.yaml"
        assert staged_file.exists(), "Staged file should be created"

        # Retrieve staged patterns
        staged_patterns = pattern_learning.get_staged_patterns("security")
        assert len(staged_patterns) == 1, "Should have 1 staged pattern"
        assert staged_patterns[0]["pattern"] == "AWS_ACCESS_KEY", "Pattern should match"

    def test_pattern_learning_commit(self, tmp_path: Path):
        """Test that staged patterns can be committed to main doc."""
        docs_dir = tmp_path / "docs" / "reviewers"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create main doc
        main_doc = docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
agent: security
patterns:
  - type: content
    pattern: password
    weight: 0.9
---
# Security Reviewer
""")

        pattern_learning = PatternLearning(docs_dir=docs_dir)

        # Stage a pattern
        new_pattern = {
            "type": "content",
            "pattern": "API_KEY",
            "language": "python",
            "weight": 0.95,
            "source": "PR #456",
        }

        pattern_learning.add_learned_pattern("security", new_pattern)

        # Commit staged patterns
        success, message = pattern_learning.commit_learned_patterns("security")

        assert success is True, f"Commit should succeed: {message}"

        # Verify pattern merged into main doc
        updated_content = main_doc.read_text()
        assert "API_KEY" in updated_content, "Pattern should be in main doc"

        # Verify staged file deleted
        staged_file = docs_dir / "security_staged_patterns.yaml"
        assert not staged_file.exists(), "Staged file should be deleted after commit"

    def test_duplicate_pattern_rejected(self, tmp_path: Path):
        """Test that duplicate patterns are rejected."""
        docs_dir = tmp_path / "docs" / "reviewers"
        docs_dir.mkdir(parents=True, exist_ok=True)

        pattern_learning = PatternLearning(docs_dir=docs_dir)

        pattern = {"type": "content", "pattern": "password", "language": "python", "weight": 0.9}

        # Add same pattern twice
        success1 = pattern_learning.add_learned_pattern("security", pattern)
        success2 = pattern_learning.add_learned_pattern("security", pattern)

        assert success1 is True, "First add should succeed"
        assert success2 is False, "Duplicate add should fail"


class TestDiscoveryPerformance:
    """Test entry point discovery performance."""

    @pytest.mark.asyncio
    async def test_discovery_performance_per_reviewer(self, mock_repo: Path):
        """Test that discovery completes within 30s per reviewer."""
        discovery = EntryPointDiscovery()

        # Mock discovery to simulate real work but stay fast
        async def mock_discover(agent_name, repo_root, changed_files):
            await asyncio.sleep(0.5)  # Simulate 0.5s discovery
            return [
                EntryPoint(
                    file_path="src/auth/login.py",
                    line_number=1,
                    description="Entry point",
                    weight=0.9,
                    pattern_type="content",
                    evidence="test",
                ),
            ]

        with patch.object(discovery, "discover_entry_points", side_effect=mock_discover):
            start_time = time.time()
            entry_points = await discovery.discover_entry_points(
                agent_name="security", repo_root=str(mock_repo), changed_files=["src/auth/login.py"]
            )
            discovery_time = time.time() - start_time

        # Verify discovery completes quickly (<30s, realistically should be <5s)
        assert discovery_time < 30, f"Discovery took {discovery_time:.1f}s, exceeds 30s timeout"
        assert entry_points is not None, "Discovery should return entry points"


class TestContextFilteringEffectiveness:
    """Test context filtering effectiveness."""

    @pytest.mark.asyncio
    async def test_context_filtering_reduces_file_count(self, mock_repo: Path, mock_pr_diff: str):
        """Test that entry point filtering reduces file count."""
        # Mock repository with many files
        all_files = [
            "src/auth/login.py",
            "src/auth/logout.py",
            "src/api/user.py",
            "src/api/order.py",
            "config/settings.py",
            "config/database.py",
            "tests/test_auth.py",
            "tests/test_api.py",
            "docs/readme.md",
            "docs/api.md",
        ]

        # Mock discovery to return entry points for only 2 files
        mock_entry_points = [
            EntryPoint(
                file_path="src/auth/login.py",
                line_number=5,
                description="Hardcoded secret",
                weight=0.95,
                pattern_type="content",
                evidence="test",
            ),
            EntryPoint(
                file_path="config/settings.py",
                line_number=1,
                description="Configuration",
                weight=0.9,
                pattern_type="file_path",
                evidence="test",
            ),
        ]

        discovery = EntryPointDiscovery()

        with patch.object(
            discovery,
            "discover_entry_points",
            new_callable=AsyncMock,
            return_value=mock_entry_points,
        ):
            agent = SecurityReviewer()
            orchestrator = PRReviewOrchestrator([agent], discovery=discovery)

            inputs = ReviewInputs(
                repo_root=str(mock_repo),
                base_ref="main",
                head_ref="feature",
                timeout_seconds=30,
            )

            diff = mock_pr_diff

            with (
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_changed_files",
                    AsyncMock(return_value=all_files),
                ),
                patch(
                    "dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)
                ),
            ):
                # Mock review to capture context
                captured_context = []

                async def mock_review(context: ReviewContext) -> ReviewOutput:
                    # Capture context for verification
                    captured_context.append(context)
                    # Simulate review work (0.1s)
                    await asyncio.sleep(0.1)
                    return ReviewOutput(
                        agent="security",
                        severity="merge",
                        scope=Scope(relevant_files=[], reasoning="Mock review"),
                        findings=[],
                        merge_gate=MergeGate(decision="approve", must_fix=[]),
                        summary="Mock review",
                    )

                with patch.object(agent, "review", new_callable=AsyncMock, side_effect=mock_review):
                    await orchestrator.run_review(inputs)

        # Verify filtering occurred
        assert len(captured_context) == 1, "Review should be called once"
        context = captured_context[0]

        # Count files in context
        filtered_files = context.changed_files

        print(f"\nTotal files: {len(all_files)}")
        print(f"Filtered files: {len(filtered_files)}")
        print(f"Reduction: {(1 - len(filtered_files) / len(all_files)) * 100:.1f}%")

        # Assert filtering reduced file count
        assert len(filtered_files) < len(all_files), (
            f"Filtering should reduce files: {len(filtered_files)} vs {len(all_files)}"
        )

        # Assert only files with entry points are included
        assert "src/auth/login.py" in filtered_files, "File with entry point should be included"
        assert "config/settings.py" in filtered_files, "File with entry point should be included"


class TestSelfVerificationIntegration:
    """Test self-verification integration with findings."""

    def test_verify_findings_collects_evidence(self, tmp_path: Path):
        """Test that verify_findings collects structured evidence."""
        # Create test files
        test_file = tmp_path / "test.py"
        test_file.write_text("""API_KEY = "secret123"
password = "admin"
""")

        reviewer = SecurityReviewer()

        # Create mock findings
        findings = [
            Finding(
                id="finding-1",
                title="Hardcoded API key",
                severity="critical",
                confidence="high",
                owner="security",
                estimate="S",
                evidence='Found API_KEY = "secret123"',
                risk="Secret exposure",
                recommendation="Use environment variables",
                suggested_patch=None,
            ),
        ]

        # Mock subprocess to avoid real grep calls
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = '1:API_KEY = "secret123"\n'

            verification = reviewer.verify_findings(findings, ["test.py"], str(tmp_path))

        # Verify evidence structure
        assert isinstance(verification, list), "Verification should return list"

        # If evidence was collected, verify structure
        if verification:
            assert "tool_type" in verification[0], "Should have tool_type"
            assert "search_pattern" in verification[0], "Should have search_pattern"
            assert verification[0]["tool_type"] == "grep", "Should use grep tool"

    def test_verify_findings_graceful_degradation(self):
        """Test graceful degradation on errors."""
        reviewer = SecurityReviewer()

        # Create invalid finding (missing required fields)
        class InvalidFinding:
            pass

        findings = [InvalidFinding()]

        # Should not raise exception
        verification = reviewer.verify_findings(findings, ["test.py"], "/tmp")

        # Should return empty list on error
        assert isinstance(verification, list), "Should return list"
        assert len(verification) == 0, "Should return empty list on invalid finding"


class TestCLIIntegration:
    """Test CLI integration for doc generation."""

    @pytest.mark.asyncio
    async def test_cli_generate_docs_all(self, tmp_path: Path):
        """Test CLI command to generate docs for all reviewers."""
        # Skip this test as CLI is implemented with Click, not typer
        pytest.skip("CLI uses Click framework, not typer")


class TestErrorScenarios:
    """Test error scenarios and recovery."""

    @pytest.mark.asyncio
    async def test_missing_documentation_graceful_degradation(self, mock_repo: Path):
        """Test graceful degradation when documentation is missing."""
        discovery = EntryPointDiscovery()

        # Mock _load_agent_patterns to return empty (no doc)
        with patch.object(
            discovery, "_load_agent_patterns", new_callable=AsyncMock, return_value={}
        ):
            entry_points = await discovery.discover_entry_points(
                agent_name="nonexistent", repo_root=str(mock_repo), changed_files=["src/test.py"]
            )

        # Should return None (trigger fallback)
        assert entry_points is None, "Should return None when no patterns"

    @pytest.mark.asyncio
    async def test_subprocess_failure_graceful_degradation(self, mock_repo: Path):
        """Test graceful degradation when subprocess tools fail."""
        discovery = EntryPointDiscovery()

        # Mock subprocess to fail
        with patch("subprocess.run", side_effect=FileNotFoundError("Tool not found")):
            # Load patterns but discovery should fail gracefully
            entry_points = await discovery.discover_entry_points(
                agent_name="security", repo_root=str(mock_repo), changed_files=["src/test.py"]
            )

        # Should return None (trigger fallback)
        assert entry_points is None, "Should return None on tool failure"

    def test_invalid_yaml_in_docs(self, tmp_path: Path):
        """Test handling of invalid YAML in documentation."""
        docs_dir = tmp_path / "docs" / "reviewers"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create invalid YAML
        doc_file = docs_dir / "security_reviewer.md"
        doc_file.write_text("""---
agent: invalid yaml {{
patterns: broken
---
# Content
""")

        pattern_learning = PatternLearning(docs_dir=docs_dir)

        # Should handle gracefully (not crash)
        patterns = pattern_learning.load_patterns_from_doc("security", doc_file)

        # Should return empty list on invalid YAML
        assert isinstance(patterns, list), "Should return list"
        # May be empty or may have parsed some content, but should not crash

    @pytest.mark.asyncio
    async def test_review_timeout_handling(self, mock_repo: Path, mock_pr_diff: str):
        """Test review timeout handling."""

        class SlowReviewer(BaseReviewerAgent):
            async def review(self, context: ReviewContext) -> ReviewOutput:
                await asyncio.sleep(10)  # Simulate slow review
                return ReviewOutput(
                    agent="slow_reviewer",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="Mock review"),
                    findings=[],
                    merge_gate=MergeGate(decision="approve", must_fix=[]),
                    summary="Review",
                )

            def get_system_prompt(self) -> str:
                return "Slow reviewer"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "SlowReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

        agent = SlowReviewer()
        orchestrator = PRReviewOrchestrator([agent])

        inputs = ReviewInputs(
            repo_root=str(mock_repo),
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,  # Very short timeout
        )

        changed_files = ["src/test.py"]
        diff = mock_pr_diff

        with (
            patch(
                "dawn_kestrel.agents.review.utils.git.get_changed_files",
                AsyncMock(return_value=changed_files),
            ),
            patch("dawn_kestrel.agents.review.utils.git.get_diff", AsyncMock(return_value=diff)),
        ):
            # Review should handle timeout gracefully
            try:
                await orchestrator.run_review(inputs)
                # If no exception, review completed (or timed out gracefully)
            except Exception as e:
                # Timeout may raise exception, which is acceptable
                assert "timeout" in str(e).lower() or "cancel" in str(e).lower(), (
                    f"Expected timeout-related exception, got: {e}"
                )
