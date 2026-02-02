"""Test ArchitectureReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestArchitectureReviewerLLMBased:
    """Test ArchitectureReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create an ArchitectureReviewer instance."""
        return ArchitectureReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/services/user_service.py", "src/models/user.py"],
            diff="+ class UserService:\n+     def __init__(self, db, cache, email, sms, logger, config, auth):\n+         pass",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-user-service"
        )

    @pytest.fixture
    def mock_session(self):
        """Create a mock Session object."""
        return Session(
            id="test-session-id",
            slug="test-session",
            project_id="test-project",
            directory="/test/repo",
            title="Test Session",
            version="1.0"
        )

    @pytest.fixture
    def sample_review_output_json(self):
        """Sample valid LLM response JSON."""
        return '''{
            "agent": "architecture",
            "summary": "Found 1 architectural issue(s).",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/services/user_service.py"],
                "ignored_files": [],
                "reasoning": "Architecture review analyzed 1 relevant file for boundary violations and coupling issues."
            },
            "findings": [
                {
                    "id": "ARCH-001",
                    "title": "Method with too many parameters: UserService.__init__",
                    "severity": "warning",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Method has 7 parameters indicating potential tight coupling",
                    "risk": "Methods with many parameters indicate tight coupling and poor design.",
                    "recommendation": "Consider introducing a parameter object or using dependency injection container.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["ARCH-001"],
                "notes_for_coding_agent": [
                    "Refactor to reduce parameter count and improve abstraction."
                ]
            }
        }'''

    @pytest.mark.asyncio
    async def test_review_creates_ai_session_and_calls_process_message(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() creates AISession and calls process_message()."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args

                assert isinstance(result, ReviewOutput)
                assert result.agent == "architecture"
                assert result.severity == "warning"
                assert len(result.findings) == 1
                assert result.findings[0].id == "ARCH-001"
                assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception when API key is missing."""
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise ValueError("API key not found for provider")

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                with pytest.raises(ValueError, match="API key not found"):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns error ReviewOutput for invalid JSON."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "This is not valid JSON"

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert "error" in result.summary.lower() or "invalid" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_review_handles_timeout_error_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception on timeout."""
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise TimeoutError("Request timed out after 60s")

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                with pytest.raises(TimeoutError):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_no_findings_returns_merge_severity(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns severity='merge' when no findings."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = '''{
            "agent": "architecture",
            "summary": "No architectural issues detected.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/services/user_service.py"],
                "ignored_files": [],
                "reasoning": "Architecture review analyzed 1 relevant file."
            },
            "findings": [],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }'''

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "merge"
                assert result.merge_gate.decision == "approve"
                assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_review_includes_system_prompt_and_context_in_message(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() includes system prompt and formatted context."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        captured_message = None

        async def mock_process_message(user_message, options=None):
            nonlocal captured_message
            captured_message = user_message
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/services/user_service.py" in captured_message
                assert sample_context.diff in captured_message

    @pytest.mark.asyncio
    async def test_review_with_boundary_violation_finding(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() correctly handles boundary violation findings."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = '''{
            "agent": "architecture",
            "summary": "Boundary violation detected.",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/api/handlers.py"],
                "ignored_files": [],
                "reasoning": "Detected cross-layer dependency violation."
            },
            "findings": [
                {
                    "id": "ARCH-BOUNDARY-001",
                    "title": "Boundary violation: presentation imports infrastructure",
                    "severity": "warning",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "src/api/handlers.py:45 imports from infrastructure.database",
                    "risk": "Direct infrastructure imports in presentation layer violate clean architecture principles.",
                    "recommendation": "Introduce an application service or repository interface to abstract infrastructure concerns.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["ARCH-BOUNDARY-001"],
                "notes_for_coding_agent": [
                    "Add repository interface to separate concerns."
                ]
            }
        }'''

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "warning"
                assert len(result.findings) == 1
                assert result.findings[0].id == "ARCH-BOUNDARY-001"
                assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_with_circular_dependency_finding(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() correctly handles circular dependency findings."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = '''{
            "agent": "architecture",
            "summary": "Circular dependency detected.",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/services/user.py", "src/models/user.py"],
                "ignored_files": [],
                "reasoning": "Detected circular import between modules."
            },
            "findings": [
                {
                    "id": "ARCH-CIRCULAR-001",
                    "title": "Potential circular dependency detected",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Cross-module imports found:\\nsrc/services/user.py imports from src.models.user\\nsrc/models/user.py imports from src.services.user",
                    "risk": "Circular dependencies can cause import-time errors and make code hard to test.",
                    "recommendation": "Refactor to use dependency injection or introduce a new module to break the cycle.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["ARCH-CIRCULAR-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Break circular dependency by introducing new module."
                ]
            }
        }'''

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.architecture.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.architecture.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert len(result.findings) == 1
                assert result.findings[0].id == "ARCH-CIRCULAR-001"
                assert result.merge_gate.decision == "needs_changes"
                assert "ARCH-CIRCULAR-001" in result.merge_gate.must_fix
