"""Comprehensive tests for pattern learning mechanism."""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import List
from unittest.mock import MagicMock, patch

from dawn_kestrel.agents.review.pattern_learning import PatternLearning
from dawn_kestrel.agents.review.base import BaseReviewerAgent


class TestPatternLearning:
    """Test PatternLearning class methods."""

    @pytest.fixture
    def temp_docs_dir(self):
        """Create a temporary directory for test docs."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def pattern_learning(self, temp_docs_dir):
        """Create PatternLearning instance with temp directory."""
        return PatternLearning(docs_dir=temp_docs_dir)

    @pytest.fixture
    def valid_ast_pattern(self):
        """Create a valid AST pattern."""
        return {
            "type": "ast",
            "pattern": "FunctionDef",
            "weight": 0.9,
            "language": "python",
            "source": "Test pattern",
        }

    @pytest.fixture
    def valid_content_pattern(self):
        """Create a valid content pattern."""
        return {
            "type": "content",
            "pattern": r"API_KEY\s*[=:]",
            "weight": 0.95,
            "language": "python",
            "source": "PR #123",
        }

    @pytest.fixture
    def valid_file_path_pattern(self):
        """Create a valid file_path pattern."""
        return {"type": "file_path", "pattern": "config/*.yaml", "weight": 0.8, "source": "PR #456"}

    @pytest.fixture
    def sample_doc_content(self):
        """Create sample documentation content with YAML frontmatter."""
        return """---
title: Security Reviewer
patterns:
  - type: content
    pattern: "password\\s*="
    language: python
    weight: 0.9
  - type: ast
    pattern: "eval"
    language: python
    weight: 0.85
heuristics:
  - name: Check for hardcoded credentials
    description: Look for literal passwords or keys
---

# Security Reviewer

This reviewer checks for security issues.
"""

    # Test 1: add_learned_pattern() with valid pattern (ast type)
    def test_add_learned_pattern_with_valid_ast_pattern(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test adding a valid AST pattern."""
        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is True
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"
        assert staged_file.exists()
        content = staged_file.read_text()
        assert "learned_patterns:" in content
        assert "type: ast" in content
        assert "FunctionDef" in content

    # Test 1: add_learned_pattern() with valid pattern (content type)
    def test_add_learned_pattern_with_valid_content_pattern(
        self, pattern_learning, temp_docs_dir, valid_content_pattern
    ):
        """Test adding a valid content pattern."""
        result = pattern_learning.add_learned_pattern("security", valid_content_pattern)

        assert result is True
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"
        assert staged_file.exists()
        content = staged_file.read_text()
        assert "type: content" in content
        assert "API_KEY" in content

    # Test 1: add_learned_pattern() with valid pattern (file_path type)
    def test_add_learned_pattern_with_valid_file_path_pattern(
        self, pattern_learning, temp_docs_dir, valid_file_path_pattern
    ):
        """Test adding a valid file_path pattern."""
        result = pattern_learning.add_learned_pattern("security", valid_file_path_pattern)

        assert result is True
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"
        assert staged_file.exists()
        content = staged_file.read_text()
        assert "type: file_path" in content
        assert "config/*.yaml" in content

    # Test 2: add_learned_pattern() with invalid pattern (missing required fields)
    def test_add_learned_pattern_with_missing_required_fields(
        self, pattern_learning, temp_docs_dir
    ):
        """Test adding a pattern with missing required fields."""
        # Missing 'weight' field
        invalid_pattern = {"type": "ast", "pattern": "FunctionDef", "language": "python"}

        result = pattern_learning.add_learned_pattern("security", invalid_pattern)

        assert result is False
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"
        assert not staged_file.exists()

    # Test 2: add_learned_pattern() with invalid pattern (missing 'type')
    def test_add_learned_pattern_with_missing_type(self, pattern_learning, temp_docs_dir):
        """Test adding a pattern with missing type field."""
        invalid_pattern = {"pattern": "FunctionDef", "weight": 0.9, "language": "python"}

        result = pattern_learning.add_learned_pattern("security", invalid_pattern)

        assert result is False

    # Test 2: add_learned_pattern() with invalid pattern (missing 'pattern')
    def test_add_learned_pattern_with_missing_pattern_field(self, pattern_learning, temp_docs_dir):
        """Test adding a pattern with missing pattern field."""
        invalid_pattern = {"type": "ast", "weight": 0.9, "language": "python"}

        result = pattern_learning.add_learned_pattern("security", invalid_pattern)

        assert result is False

    # Test 3: add_learned_pattern() with invalid weight (out of 0.0-1.0 range)
    def test_add_learned_pattern_with_weight_too_high(self, pattern_learning, valid_ast_pattern):
        """Test adding a pattern with weight > 1.0."""
        valid_ast_pattern["weight"] = 1.5

        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is False

    # Test 3: add_learned_pattern() with invalid weight (negative)
    def test_add_learned_pattern_with_negative_weight(self, pattern_learning, valid_ast_pattern):
        """Test adding a pattern with negative weight."""
        valid_ast_pattern["weight"] = -0.1

        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is False

    # Test 3: add_learned_pattern() with invalid weight type
    def test_add_learned_pattern_with_invalid_weight_type(
        self, pattern_learning, valid_ast_pattern
    ):
        """Test adding a pattern with non-numeric weight."""
        valid_ast_pattern["weight"] = "high"

        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is False

    # Test 4: add_learned_pattern() with missing language for ast type
    def test_add_learned_pattern_with_missing_language_for_ast(
        self, pattern_learning, valid_ast_pattern
    ):
        """Test adding AST pattern without language (should fail)."""
        del valid_ast_pattern["language"]

        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is False

    # Test 5: add_learned_pattern() with missing language for content type
    def test_add_learned_pattern_with_missing_language_for_content(
        self, pattern_learning, valid_content_pattern
    ):
        """Test adding content pattern without language (should fail)."""
        del valid_content_pattern["language"]

        result = pattern_learning.add_learned_pattern("security", valid_content_pattern)

        assert result is False

    # Test 6: add_learned_pattern() with file_path type without language (valid)
    def test_add_learned_pattern_with_file_path_without_language(
        self, pattern_learning, valid_file_path_pattern
    ):
        """Test adding file_path pattern without language (should succeed)."""
        # file_path type doesn't require language
        assert "language" not in valid_file_path_pattern

        result = pattern_learning.add_learned_pattern("security", valid_file_path_pattern)

        assert result is True

    # Test 7: add_learned_pattern() duplicate detection (same type + pattern)
    def test_add_learned_pattern_duplicate_detection(self, pattern_learning, valid_ast_pattern):
        """Test that duplicate patterns are detected and rejected."""
        # Add pattern first time
        result1 = pattern_learning.add_learned_pattern("security", valid_ast_pattern)
        assert result1 is True

        # Try to add same pattern again
        result2 = pattern_learning.add_learned_pattern("security", valid_ast_pattern)
        assert result2 is False

        # Verify only one pattern in staged file
        staged_patterns = pattern_learning.get_staged_patterns("security")
        assert len(staged_patterns) == 1

    # Test 7: add_learned_pattern() duplicate detection with different type
    def test_add_learned_pattern_different_types_not_duplicate(
        self, pattern_learning, temp_docs_dir
    ):
        """Test that same pattern string with different types is not considered duplicate."""
        pattern1 = {"type": "ast", "pattern": "eval", "weight": 0.9, "language": "python"}
        pattern2 = {"type": "content", "pattern": "eval", "weight": 0.8, "language": "python"}

        result1 = pattern_learning.add_learned_pattern("security", pattern1)
        result2 = pattern_learning.add_learned_pattern("security", pattern2)

        assert result1 is True
        assert result2 is True

        staged_patterns = pattern_learning.get_staged_patterns("security")
        assert len(staged_patterns) == 2

    # Test 8: get_staged_patterns() with no staged patterns (returns empty list)
    def test_get_staged_patterns_with_no_staged_patterns(self, pattern_learning):
        """Test getting staged patterns when none exist."""
        patterns = pattern_learning.get_staged_patterns("nonexistent_agent")

        assert patterns == []

    # Test 9: get_staged_patterns() with staged patterns (returns list)
    def test_get_staged_patterns_returns_list(
        self, pattern_learning, valid_ast_pattern, valid_content_pattern
    ):
        """Test getting staged patterns returns correct list."""
        pattern_learning.add_learned_pattern("security", valid_ast_pattern)
        pattern_learning.add_learned_pattern("security", valid_content_pattern)

        patterns = pattern_learning.get_staged_patterns("security")

        assert len(patterns) == 2
        assert patterns[0]["type"] == "ast"
        assert patterns[1]["type"] == "content"
        assert "FunctionDef" in patterns[0]["pattern"]
        assert "API_KEY" in patterns[1]["pattern"]

    # Test 10: commit_learned_patterns() merges staged into main doc
    def test_commit_learned_patterns_merges_staged(
        self, pattern_learning, temp_docs_dir, valid_content_pattern, sample_doc_content
    ):
        """Test committing staged patterns merges them into main doc."""
        # Create main doc
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text(sample_doc_content)

        # Add staged pattern
        pattern_learning.add_learned_pattern("security", valid_content_pattern)

        # Commit staged patterns
        success, message = pattern_learning.commit_learned_patterns("security")

        assert success is True
        assert "Committed" in message

        # Verify main doc is updated
        updated_content = main_doc.read_text()
        assert "API_KEY" in updated_content

        # Verify staged file is deleted
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"
        assert not staged_file.exists()

    # Test 11: commit_learned_patterns() with duplicates (deduplicates)
    def test_commit_learned_patterns_deduplicates(
        self, pattern_learning, temp_docs_dir, valid_content_pattern
    ):
        """Test committing patterns deduplicates against existing ones."""
        # Create main doc with existing pattern (include heuristics section)
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
patterns:
  - type: content
    pattern: "password\\s*="
    language: python
    weight: 0.9
heuristics:
  - name: Check for passwords
    description: Look for password patterns
---

# Security Reviewer
""")

        # Add staged pattern with duplicate pattern string
        valid_content_pattern["pattern"] = "password\\s*="
        pattern_learning.add_learned_pattern("security", valid_content_pattern)

        # Commit
        success, message = pattern_learning.commit_learned_patterns("security")

        assert success is True

        # Verify only one pattern exists (deduplicated)
        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)
        assert len(patterns) == 1

    # Test 12: commit_learned_patterns() with no staged patterns (no changes)
    def test_commit_learned_patterns_with_no_staged_patterns(
        self, pattern_learning, temp_docs_dir, sample_doc_content
    ):
        """Test committing when no staged patterns exist."""
        # Create main doc
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text(sample_doc_content)

        # Try to commit without staged patterns
        success, message = pattern_learning.commit_learned_patterns("security")

        assert success is False
        assert "No staged patterns" in message

        # Verify main doc unchanged
        content = main_doc.read_text()
        assert content == sample_doc_content

    # Test 13: commit_learned_patterns() with no main doc (returns error)
    def test_commit_learned_patterns_with_no_main_doc(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test committing when main doc doesn't exist."""
        # Add staged pattern
        pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        # Try to commit without main doc
        success, message = pattern_learning.commit_learned_patterns("security")

        assert success is False
        assert "not found" in message

    # Test 14: load_patterns_from_doc() with valid YAML frontmatter
    def test_load_patterns_from_doc_with_valid_yaml(
        self, pattern_learning, temp_docs_dir, sample_doc_content
    ):
        """Test loading patterns from doc with valid YAML."""
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text(sample_doc_content)

        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)

        assert len(patterns) == 2
        assert patterns[0]["type"] == "content"
        assert patterns[1]["type"] == "ast"
        assert "password" in patterns[0]["pattern"]
        assert "eval" in patterns[1]["pattern"]

    # Test 15: load_patterns_from_doc() with nonexistent doc (returns empty list)
    def test_load_patterns_from_doc_with_nonexistent_doc(self, pattern_learning, temp_docs_dir):
        """Test loading patterns from nonexistent doc."""
        nonexistent_doc = temp_docs_dir / "nonexistent_reviewer.md"

        patterns = pattern_learning.load_patterns_from_doc("nonexistent", nonexistent_doc)

        assert patterns == []

    # Test 16: load_patterns_from_doc() with invalid YAML (returns empty list)
    def test_load_patterns_from_doc_with_invalid_yaml(self, pattern_learning, temp_docs_dir):
        """Test loading patterns from doc with invalid YAML."""
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""
---
invalid yaml: [unclosed bracket
patterns:
  - type: content
---

# Security Reviewer
""")

        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)

        # Should return empty list on error (graceful degradation)
        assert patterns == []

    # Test 16: load_patterns_from_doc() with no YAML frontmatter (returns empty list)
    def test_load_patterns_from_doc_with_no_frontmatter(self, pattern_learning, temp_docs_dir):
        """Test loading patterns from doc without YAML frontmatter."""
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""
# Security Reviewer

This doc has no YAML frontmatter.
""")

        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)

        assert patterns == []

    # Test 16: load_patterns_from_doc() with no patterns section (returns empty list)
    def test_load_patterns_from_doc_with_no_patterns_section(self, pattern_learning, temp_docs_dir):
        """Test loading patterns from doc with YAML but no patterns section."""
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
title: Security Reviewer
heuristics:
  - name: Check for hardcoded credentials
---

# Security Reviewer
""")

        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)

        assert patterns == []

    # Test 17: Multi-line array parsing in YAML (test save/load cycle)
    def test_multiline_pattern_save_load_cycle(self, pattern_learning, temp_docs_dir):
        """Test that patterns with special regex characters are saved and loaded correctly."""
        # Pattern with special regex characters
        complex_pattern = {
            "type": "content",
            "pattern": r'AWS_ACCESS_KEY\s*[=:]\s*["\'][A-Za-z0-9+/=]{20,}["\']',
            "weight": 0.95,
            "language": "python",
            "source": "PR #789",
        }

        # Add pattern
        pattern_learning.add_learned_pattern("security", complex_pattern)

        # Load from staged file
        patterns = pattern_learning.get_staged_patterns("security")

        assert len(patterns) == 1
        assert "AWS_ACCESS_KEY" in patterns[0]["pattern"]
        assert patterns[0]["weight"] == 0.95

    # Test 18: Weight sorting on merge (descending)
    def test_merge_patterns_sorted_by_weight_descending(
        self, pattern_learning, temp_docs_dir, sample_doc_content
    ):
        """Test that merged patterns are sorted by weight descending."""
        # Create main doc with low-weight pattern
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
patterns:
  - type: content
    pattern: "low_priority"
    language: python
    weight: 0.3
heuristics:
  - name: Test heuristics
    description: For testing
---

# Security Reviewer
""")

        # Add staged patterns with higher weight
        high_weight_pattern = {
            "type": "content",
            "pattern": "high_priority",
            "weight": 0.95,
            "language": "python",
        }
        medium_weight_pattern = {
            "type": "content",
            "pattern": "medium_priority",
            "weight": 0.7,
            "language": "python",
        }
        pattern_learning.add_learned_pattern("security", medium_weight_pattern)
        pattern_learning.add_learned_pattern("security", high_weight_pattern)

        # Commit
        pattern_learning.commit_learned_patterns("security")

        # Load patterns and verify sorting
        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)
        weights = [p["weight"] for p in patterns]

        assert weights == sorted(weights, reverse=True)
        assert weights[0] == 0.95
        assert weights[1] == 0.7
        assert weights[2] == 0.3

    # Test 19: Staged file creation and deletion
    def test_staged_file_creation_and_deletion(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test that staged file is created and properly deleted on commit."""
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"

        # Verify no staged file initially
        assert not staged_file.exists()

        # Add pattern (creates staged file)
        pattern_learning.add_learned_pattern("security", valid_ast_pattern)
        assert staged_file.exists()

        # Create main doc for commit
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text(
            sample_doc_content := """---
patterns:
  - type: ast
    pattern: "FunctionDef"
    language: python
    weight: 0.9
---

# Security Reviewer
"""
        )

        # Commit (deletes staged file)
        pattern_learning.commit_learned_patterns("security")
        assert not staged_file.exists()

    # Test 20: File I/O error handling (graceful degradation)
    def test_add_learned_pattern_handles_io_errors(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test that file I/O errors are handled gracefully."""
        # Make directory read-only (simulating permission error)
        # Note: This may not work on all systems, but tests the error handling path
        import os

        # Create a read-only directory
        readonly_dir = temp_docs_dir / "readonly"
        readonly_dir.mkdir()

        try:
            os.chmod(str(readonly_dir), 0o444)

            # Try to add pattern to readonly dir
            readonly_learning = PatternLearning(docs_dir=readonly_dir)
            result = readonly_learning.add_learned_pattern("security", valid_ast_pattern)

            # Should return False on error
            assert result is False

        finally:
            # Restore permissions for cleanup
            os.chmod(str(readonly_dir), 0o755)

    # Test 20: File I/O error handling (load from corrupted file)
    def test_load_staged_patterns_handles_corrupted_file(self, pattern_learning, temp_docs_dir):
        """Test that corrupted staged file is handled gracefully."""
        staged_file = temp_docs_dir / "security_staged_patterns.yaml"

        # Write corrupted content
        staged_file.write_text("""
invalid yaml: [
  unclosed bracket: {
    pattern: "test"
""")

        # Should return empty list on error
        patterns = pattern_learning.get_staged_patterns("security")

        assert patterns == []

    # Test 21: BaseReviewerAgent.learn_entry_point_pattern() default implementation
    def test_base_reviewer_agent_learn_entry_point_pattern_default(self, caplog):
        """Test that BaseReviewerAgent.learn_entry_point_pattern() returns False by default."""

        # Create a concrete instance (can't instantiate abstract class directly)
        class TestReviewer(BaseReviewerAgent):
            async def review(self, context):
                pass

            def get_system_prompt(self):
                return "test"

            def get_relevant_file_patterns(self):
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

        reviewer = TestReviewer()
        pattern = {"type": "content", "pattern": "test", "weight": 0.5}

        # Capture logs
        with caplog.at_level("DEBUG"):
            result = reviewer.learn_entry_point_pattern(pattern)

        assert result is False

        # Verify debug log was created
        assert "not implemented" in caplog.text.lower()

    # Test 22: BaseReviewerAgent.learn_entry_point_pattern() override example
    def test_base_reviewer_agent_learn_entry_point_pattern_override(self, temp_docs_dir):
        """Test overriding learn_entry_point_pattern() with PatternLearning."""

        class LearningReviewer(BaseReviewerAgent):
            """Reviewer that learns patterns."""

            def __init__(self):
                super().__init__()
                self.pattern_learning = PatternLearning(docs_dir=temp_docs_dir)
                self.name = "learning_reviewer"

            async def review(self, context):
                pass

            def get_system_prompt(self):
                return "test"

            def get_relevant_file_patterns(self):
                return ["*.py"]

            def get_agent_name(self) -> str:
                return "LearningReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def learn_entry_point_pattern(self, pattern):
                """Override to actually learn patterns."""
                return self.pattern_learning.add_learned_pattern(self.name, pattern)

        reviewer = LearningReviewer()
        pattern = {
            "type": "content",
            "pattern": "API_KEY",
            "weight": 0.9,
            "language": "python",
            "source": "PR #999",
        }

        result = reviewer.learn_entry_point_pattern(pattern)

        assert result is True

        # Verify pattern was staged
        staged_patterns = reviewer.pattern_learning.get_staged_patterns("learning_reviewer")
        assert len(staged_patterns) == 1
        assert staged_patterns[0]["pattern"] == "API_KEY"

    # Test: Invalid type in pattern
    def test_add_learned_pattern_with_invalid_type(self, pattern_learning, temp_docs_dir):
        """Test adding pattern with invalid type."""
        invalid_pattern = {
            "type": "invalid_type",
            "pattern": "test",
            "weight": 0.5,
            "language": "python",
        }

        result = pattern_learning.add_learned_pattern("security", invalid_pattern)

        assert result is False

    # Test: Empty pattern string
    def test_add_learned_pattern_with_empty_pattern_string(self, pattern_learning, temp_docs_dir):
        """Test adding pattern with empty pattern string."""
        invalid_pattern = {"type": "content", "pattern": "", "weight": 0.5, "language": "python"}

        result = pattern_learning.add_learned_pattern("security", invalid_pattern)

        assert result is False

    # Test: Pattern with extra fields (should succeed)
    def test_add_learned_pattern_with_extra_fields(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test that extra fields in pattern are allowed."""
        valid_ast_pattern["custom_field"] = "custom_value"
        valid_ast_pattern["description"] = "This is a test pattern"

        result = pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        assert result is True

    # Test: Multiple agents can have staged patterns
    def test_multiple_agents_can_have_staged_patterns(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern, valid_content_pattern
    ):
        """Test that different agents can have separate staged patterns."""
        pattern_learning.add_learned_pattern("security", valid_ast_pattern)
        pattern_learning.add_learned_pattern("documentation", valid_content_pattern)

        security_patterns = pattern_learning.get_staged_patterns("security")
        doc_patterns = pattern_learning.get_staged_patterns("documentation")

        assert len(security_patterns) == 1
        assert len(doc_patterns) == 1
        assert security_patterns[0]["type"] == "ast"
        assert doc_patterns[0]["type"] == "content"

    # Test: Commit preserves existing patterns in doc
    def test_commit_preserves_existing_patterns(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test that commit preserves patterns already in main doc."""
        main_doc = temp_docs_dir / "security_reviewer.md"
        main_doc.write_text("""---
patterns:
  - type: content
    pattern: "existing_pattern"
    language: python
    weight: 0.7
heuristics:
  - name: Test heuristics
    description: For testing
---

# Security Reviewer
""")

        # Add new staged pattern
        pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        # Commit
        pattern_learning.commit_learned_patterns("security")

        # Load and verify both patterns exist
        patterns = pattern_learning.load_patterns_from_doc("security", main_doc)
        pattern_strings = [p["pattern"] for p in patterns]

        assert "existing_pattern" in pattern_strings
        assert "FunctionDef" in pattern_strings

    # Test: Source field is preserved in staged file
    def test_source_field_preserved_in_staged_file(
        self, pattern_learning, temp_docs_dir, valid_ast_pattern
    ):
        """Test that source field is preserved when saving to staged file."""
        valid_ast_pattern["source"] = "PR #12345 - Found critical issue"

        pattern_learning.add_learned_pattern("security", valid_ast_pattern)

        # Load from staged file
        patterns = pattern_learning.get_staged_patterns("security")

        assert len(patterns) == 1
        assert patterns[0]["source"] == "PR #12345 - Found critical issue"
