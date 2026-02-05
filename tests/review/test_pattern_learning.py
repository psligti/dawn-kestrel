"""Tests for pattern learning module."""
import pytest
from pathlib import Path
import tempfile
import shutil

from opencode_python.agents.review.pattern_learning import PatternLearning
from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput


class MockReviewerAgent(BaseReviewerAgent):
    """Mock reviewer agent for testing."""

    def __init__(self, docs_dir=None):
        self.pattern_learning = PatternLearning(docs_dir=docs_dir)

    async def review(self, context: ReviewContext) -> ReviewOutput:
        from opencode_python.agents.review.contracts import MergeGate, Scope

        return ReviewOutput(
            agent="mock",
            summary="Mock review",
            severity="merge",
            scope=Scope(
                relevant_files=context.changed_files,
                reasoning="Mock reasoning"
            ),
            merge_gate=MergeGate(decision="approve")
        )

    def get_system_prompt(self) -> str:
        return "Mock system prompt for testing"

    def get_relevant_file_patterns(self) -> list:
        return ["*.py"]

    def learn_entry_point_pattern(self, pattern: dict) -> bool:
        """Override to enable pattern learning."""
        agent_name = self.__class__.__name__.lower().replace('agent', '')
        return self.pattern_learning.add_learned_pattern(agent_name, pattern)


class TestPatternLearning:
    """Test suite for PatternLearning class."""

    def test_add_valid_pattern(self, tmp_path):
        """Test adding a valid pattern."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': r'API_KEY\s*[=:]',
            'language': 'python',
            'weight': 0.95,
            'source': 'PR #123'
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is True

        staged_patterns = learning.get_staged_patterns('mock')
        assert len(staged_patterns) == 1
        assert staged_patterns[0]['pattern'] == r'API_KEY\s*[=:]'

    def test_add_duplicate_pattern(self, tmp_path):
        """Test that duplicate patterns are rejected."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': r'API_KEY\s*[=:]',
            'language': 'python',
            'weight': 0.95
        }

        learning.add_learned_pattern('mock', pattern)
        result = learning.add_learned_pattern('mock', pattern)

        assert result is False

        staged_patterns = learning.get_staged_patterns('mock')
        assert len(staged_patterns) == 1

    def test_add_invalid_pattern_missing_type(self, tmp_path):
        """Test that patterns without type are rejected."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'pattern': r'API_KEY\s*[=:]',
            'weight': 0.95
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is False

    def test_add_invalid_pattern_weight_out_of_range(self, tmp_path):
        """Test that patterns with invalid weight are rejected."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': r'API_KEY\s*[=:]',
            'weight': 1.5
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is False

    def test_add_pattern_missing_language_for_content(self, tmp_path):
        """Test that content patterns require language."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': r'API_KEY\s*[=:]',
            'weight': 0.95
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is False

    def test_add_pattern_missing_language_for_ast(self, tmp_path):
        """Test that AST patterns require language."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'ast',
            'pattern': 'FunctionDef with decorator',
            'weight': 0.85
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is False

    def test_add_file_path_pattern_without_language(self, tmp_path):
        """Test that file_path patterns don't require language."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'file_path',
            'pattern': '**/auth/**/*.py',
            'weight': 0.7
        }

        result = learning.add_learned_pattern('mock', pattern)
        assert result is True

    def test_get_staged_patterns_empty(self, tmp_path):
        """Test getting staged patterns when none exist."""
        learning = PatternLearning(docs_dir=tmp_path)

        staged_patterns = learning.get_staged_patterns('mock')
        assert staged_patterns == []

    def test_load_patterns_from_doc(self, tmp_path):
        """Test loading patterns from documentation file."""
        learning = PatternLearning(docs_dir=tmp_path)

        doc_content = """---
agent: mock
agent_type: optional
version: 1.0.0
patterns:
  - type: content
    pattern: "API_KEY"
    language: python
    weight: 0.95
  - type: file_path
    pattern: "**/*.py"
    weight: 0.7
heuristics:
  - "Mock heuristic"
---

# Mock Documentation
"""
        doc_path = tmp_path / "mock_reviewer.md"
        doc_path.write_text(doc_content)

        patterns = learning.load_patterns_from_doc('mock', doc_path)
        assert len(patterns) == 2
        assert patterns[0]['type'] == 'content'
        assert patterns[1]['type'] == 'file_path'

    def test_load_patterns_from_nonexistent_doc(self, tmp_path):
        """Test loading patterns from non-existent file."""
        learning = PatternLearning(docs_dir=tmp_path)

        doc_path = tmp_path / "nonexistent.md"
        patterns = learning.load_patterns_from_doc('mock', doc_path)
        assert patterns == []

    def test_commit_learned_patterns(self, tmp_path):
        """Test committing staged patterns to main documentation."""
        learning = PatternLearning(docs_dir=tmp_path)

        doc_content = """---
agent: mock
agent_type: optional
version: 1.0.0
patterns:
  - type: content
    pattern: "API_KEY"
    language: python
    weight: 0.95
heuristics:
  - "Mock heuristic"
---

# Mock Documentation
"""
        doc_path = tmp_path / "mock_reviewer.md"
        doc_path.write_text(doc_content)

        new_pattern = {
            'type': 'content',
            'pattern': r'AWS_ACCESS_KEY\s*[=:]',
            'language': 'python',
            'weight': 0.95,
            'source': 'PR #123'
        }
        learning.add_learned_pattern('mock', new_pattern)

        success, message = learning.commit_learned_patterns('mock')
        assert success is True
        assert 'Committed' in message

        updated_patterns = learning.load_patterns_from_doc('mock', doc_path)
        assert len(updated_patterns) == 2

        staged_file = tmp_path / "mock_staged_patterns.yaml"
        assert not staged_file.exists()

    def test_commit_learned_patterns_with_duplicates(self, tmp_path):
        """Test committing patterns doesn't create duplicates."""
        learning = PatternLearning(docs_dir=tmp_path)

        doc_content = """---
agent: mock
agent_type: optional
version: 1.0.0
patterns:
  - type: content
    pattern: "API_KEY"
    language: python
    weight: 0.95
heuristics:
  - "Mock heuristic"
---

# Mock Documentation
"""
        doc_path = tmp_path / "mock_reviewer.md"
        doc_path.write_text(doc_content)

        duplicate_pattern = {
            'type': 'content',
            'pattern': 'API_KEY',
            'language': 'python',
            'weight': 0.95
        }
        learning.add_learned_pattern('mock', duplicate_pattern)

        new_pattern = {
            'type': 'content',
            'pattern': 'SECRET_KEY',
            'language': 'python',
            'weight': 0.9
        }
        learning.add_learned_pattern('mock', new_pattern)

        success, _ = learning.commit_learned_patterns('mock')
        assert success is True

        updated_patterns = learning.load_patterns_from_doc('mock', doc_path)
        assert len(updated_patterns) == 2
        pattern_strings = [p['pattern'] for p in updated_patterns]
        assert 'API_KEY' in pattern_strings
        assert 'SECRET_KEY' in pattern_strings

    def test_commit_learned_patterns_no_staged(self, tmp_path):
        """Test committing when no staged patterns exist."""
        learning = PatternLearning(docs_dir=tmp_path)

        doc_content = """---
agent: mock
agent_type: optional
version: 1.0.0
patterns:
  - type: content
    pattern: "API_KEY"
    language: python
    weight: 0.95
heuristics:
  - "Mock heuristic"
---

# Mock Documentation
"""
        doc_path = tmp_path / "mock_reviewer.md"
        doc_path.write_text(doc_content)

        success, message = learning.commit_learned_patterns('mock')
        assert success is False
        assert 'No staged patterns' in message

    def test_commit_learned_patterns_no_main_doc(self, tmp_path):
        """Test committing when main documentation doesn't exist."""
        learning = PatternLearning(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': 'API_KEY',
            'language': 'python',
            'weight': 0.95
        }
        learning.add_learned_pattern('mock', pattern)

        success, message = learning.commit_learned_patterns('mock')
        assert success is False
        assert 'Main documentation not found' in message


class TestBaseReviewerAgentPatternLearning:
    """Test suite for BaseReviewerAgent.learn_entry_point_pattern method."""

    def test_default_implementation_returns_false(self):
        """Test that default implementation returns False."""
        class DefaultAgent(BaseReviewerAgent):
            """Agent that uses default learn_entry_point_pattern."""

            async def review(self, context: ReviewContext) -> ReviewOutput:
                from opencode_python.agents.review.contracts import MergeGate, Scope

                return ReviewOutput(
                    agent="default",
                    summary="Default review",
                    severity="merge",
                    scope=Scope(
                        relevant_files=context.changed_files,
                        reasoning="Default reasoning"
                    ),
                    merge_gate=MergeGate(decision="approve")
                )

            def get_system_prompt(self) -> str:
                return "Default system prompt"

            def get_relevant_file_patterns(self) -> list:
                return ["*.py"]

        agent = DefaultAgent()

        pattern = {
            'type': 'content',
            'pattern': 'API_KEY',
            'language': 'python',
            'weight': 0.95
        }

        result = agent.learn_entry_point_pattern(pattern)
        assert result is False

    def test_override_implementation_works(self, tmp_path):
        """Test that overriding learn_entry_point_pattern works."""
        agent = MockReviewerAgent(docs_dir=tmp_path)

        pattern = {
            'type': 'content',
            'pattern': 'API_KEY',
            'language': 'python',
            'weight': 0.95
        }

        result = agent.learn_entry_point_pattern(pattern)
        assert result is True
