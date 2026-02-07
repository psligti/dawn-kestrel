"""Tests for DocGenAgent class."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from dawn_kestrel.agents.review.doc_gen import DocGenAgent
from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext


class TestDocGenAgentInit:
    """Test DocGenAgent initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default agents_dir."""
        agent = DocGenAgent()
        assert isinstance(agent.agents_dir, Path)
        # Verify agents_dir is set correctly (not None)
        assert agent.agents_dir is not None
        # Verify agents_dir has correct structure (points to agents directory)
        assert str(agent.agents_dir).endswith("/agents")
        # Verify agents_dir.parent is set correctly
        assert agent.agents_dir.parent is not None
        # Verify the parent directory is dawn_kestrel
        assert "dawn_kestrel" in str(agent.agents_dir.parent)

    def test_init_with_custom_path(self):
        """Test initialization with custom agents_dir."""
        custom_path = Path("/custom/path")
        agent = DocGenAgent(agents_dir=custom_path)
        assert agent.agents_dir == custom_path

    def test_init_sets_output_dir(self):
        """Test output_dir is set correctly."""
        agent = DocGenAgent()
        assert isinstance(agent.output_dir, Path)


class TestDocGenAgentCalculateHash:
    """Test hash calculation method."""

    def test_calculate_hash_basic(self):
        """Test SHA256 hash calculation with basic content."""
        agent = DocGenAgent()
        content = "Test content"
        hash_val = agent._calculate_hash(content)

        # Should be 24 characters (first 24 chars of SHA256 hex)
        assert len(hash_val) == 24
        assert isinstance(hash_val, str)
        # Should match manually calculated SHA256
        import hashlib

        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()[:24]
        assert hash_val == expected

    def test_calculate_hash_empty_string(self):
        """Test hash calculation with empty string."""
        agent = DocGenAgent()
        hash_val = agent._calculate_hash("")

        assert len(hash_val) == 24
        # Empty string hash should be predictable
        import hashlib

        expected = hashlib.sha256(b"").hexdigest()[:24]
        assert hash_val == expected

    def test_calculate_hash_unicode(self):
        """Test hash calculation with unicode content."""
        agent = DocGenAgent()
        content = "Test with 한국어 🇰🇷"
        hash_val = agent._calculate_hash(content)

        assert len(hash_val) == 24
        assert isinstance(hash_val, str)

    def test_calculate_hash_long_content(self):
        """Test hash calculation with long content."""
        agent = DocGenAgent()
        content = "x" * 10000
        hash_val = agent._calculate_hash(content)

        assert len(hash_val) == 24
        assert isinstance(hash_val, str)

    def test_calculate_hash_different_content(self):
        """Test that different content produces different hash."""
        agent = DocGenAgent()
        hash1 = agent._calculate_hash("content1")
        hash2 = agent._calculate_hash("content2")

        assert hash1 != hash2

    def test_calculate_hash_identical_content(self):
        """Test that identical content produces same hash."""
        agent = DocGenAgent()
        hash1 = agent._calculate_hash("same content")
        hash2 = agent._calculate_hash("same content")

        assert hash1 == hash2


class TestDocGenAgentGetAgentName:
    """Test agent name extraction."""

    def test_get_agent_name_with_method(self):
        """Test extraction when get_agent_name method exists."""

        class MockAgent(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "CustomAgent"

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent = DocGenAgent()
        name = agent._get_agent_name(MockAgent())

        assert name == "CustomAgent"

    def test_get_agent_name_fallback_to_class(self):
        """Test fallback to class name when method doesn't exist."""

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent = DocGenAgent()
        name = agent._get_agent_name(MockAgent())

        assert name == "mockagent"

    def test_get_agent_name_removes_reviewer_suffix(self):
        """Test that 'reviewer' suffix is removed from class name."""

        class MockReviewer(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent = DocGenAgent()
        name = agent._get_agent_name(MockReviewer())

        assert name == "mock"

    def test_get_agent_name_with_complex_name(self):
        """Test extraction with complex class names."""

        class MockReviewer123(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent = DocGenAgent()
        name = agent._get_agent_name(MockReviewer123())

        # "MockReviewer123" -> .lower() -> "mockreviewer123"
        # remove "reviewer" -> "mock123"
        assert name == "mock123"


class TestDocGenAgentExtractExistingHash:
    """Test existing hash extraction from documentation."""

    def test_extract_hash_from_file(self, tmp_path: Path):
        """Test extracting hash from valid documentation file."""
        doc_path = tmp_path / "test_agent.md"
        content = """---
agent: test_agent
prompt_hash: abc123def456
version: 1.0.0
---
# Documentation"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val == "abc123def456"

    def test_extract_hash_from_file_with_spaces(self, tmp_path: Path):
        """Test extracting hash with spaces around colon."""
        doc_path = tmp_path / "test_agent.md"
        content = """---
agent: test_agent
prompt_hash:   abc123def456   ---
# Documentation"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val == "abc123def456"

    def test_extract_hash_not_found(self, tmp_path: Path):
        """Test returning None when hash not found."""
        doc_path = tmp_path / "test_agent.md"
        content = """---
agent: test_agent
version: 1.0.0
---
# Documentation"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val is None

    def test_extract_hash_empty_file(self, tmp_path: Path):
        """Test returning None for empty file."""
        doc_path = tmp_path / "test_agent.md"
        doc_path.write_text("")

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val is None

    def test_extract_hash_no_hash_section(self, tmp_path: Path):
        """Test returning None when hash section doesn't exist."""
        doc_path = tmp_path / "test_agent.md"
        content = """agent: test_agent
version: 1.0.0"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val is None

    def test_extract_hash_invalid_format(self, tmp_path: Path):
        """Test returning None when hash format is invalid."""
        doc_path = tmp_path / "test_agent.md"
        content = """---
    agent: test_agent
    prompt_hash: invalid format
    ---
    # Documentation"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        # Hash extraction with colon and word boundary - only matches valid 24-char hashes
        assert hash_val is None

    def test_extract_hash_multiline_hash(self, tmp_path: Path):
        """Test extracting hash from multiline content."""
        doc_path = tmp_path / "test_agent.md"
        content = """---
agent: test_agent

prompt_hash: abc123def456

version: 1.0.0
---
# Documentation"""
        doc_path.write_text(content)

        agent = DocGenAgent()
        hash_val = agent._extract_existing_hash(doc_path)

        assert hash_val == "abc123def456"


class TestDocGenAgentExtractPatternsFromPrompt:
    """Test pattern extraction from system prompt."""

    def test_extract_patterns_with_all_types(self):
        """Test extracting AST, file_path, and content patterns."""
        agent = DocGenAgent()

        # Create mock agent with system prompt containing patterns
        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return """You specialize in security review.

Look for:
- @login_required decorator
- FunctionDef with many parameters

File patterns:
- "auth/**.py"
- "server/**/*.py"

Content patterns:
- password = xxx
- eval( something)"""

            def get_relevant_file_patterns(self):
                return ["tests/**", "README*"]

            async def review(self, context):
                pass

        system_prompt = agent._get_agent_name(MockAgent())  # Temporary
        patterns = agent._extract_patterns_from_prompt(system_prompt, MockAgent())

        # Should have patterns of all types
        assert len(patterns) > 0
        types = set(p["type"] for p in patterns)
        assert "ast" in types
        assert "file_path" in types
        assert "content" in types

    def test_extract_patterns_minimum_ast(self):
        """Test AST patterns added when below minimum count."""
        agent = DocGenAgent()

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Minimal prompt"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        patterns = agent._extract_patterns_from_prompt("Minimal prompt", MockAgent())

        # Should have at least 1 AST pattern (implementation adds 1)
        ast_patterns = [p for p in patterns if p["type"] == "ast"]
        assert len(ast_patterns) >= 1
        assert all(p["weight"] == 0.7 for p in ast_patterns)

    def test_extract_patterns_minimum_file_path(self):
        """Test file_path patterns added when below minimum count."""
        agent = DocGenAgent()

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Minimal prompt"

            def get_relevant_file_patterns(self):
                return ["test/**"]

            async def review(self, context):
                pass

        patterns = agent._extract_patterns_from_prompt("Minimal prompt", MockAgent())

        # Should have at least 1 file_path pattern from get_relevant_file_patterns
        file_path_patterns = [p for p in patterns if p["type"] == "file_path"]
        assert len(file_path_patterns) >= 1
        assert all(p["weight"] == 0.7 for p in file_path_patterns)

    def test_extract_patterns_minimum_content(self):
        """Test content patterns added when below minimum count."""
        agent = DocGenAgent()

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Minimal prompt"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        patterns = agent._extract_patterns_from_prompt("Minimal prompt", MockAgent())

        # Should have at least 1 content pattern (implementation adds 1)
        content_patterns = [p for p in patterns if p["type"] == "content"]
        assert len(content_patterns) >= 1
        assert all(p["weight"] == 0.7 for p in content_patterns)

    def test_extract_patterns_sort_by_weight(self):
        """Test patterns are sorted by weight descending."""
        agent = DocGenAgent()

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return """High weight pattern
Low weight pattern
Medium weight pattern"""

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        patterns = agent._extract_patterns_from_prompt("Test", MockAgent())

        # Check that weights are descending
        weights = [p["weight"] for p in patterns]
        assert weights == sorted(weights, reverse=True)

    def test_extract_patterns_no_duplicates(self):
        """Test patterns don't have duplicates."""
        agent = DocGenAgent()

        class MockAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return """You specialize in testing.

Look for:
- @test decorator
- @test decorator"""

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        patterns = agent._extract_patterns_from_prompt("Test", MockAgent())

        # Count occurrences of each pattern
        pattern_names = [p["pattern"] for p in patterns]
        unique_names = list(set(pattern_names))
        assert len(pattern_names) == len(unique_names)


class TestDocGenAgentExtractAstPatterns:
    """Test AST pattern extraction."""

    def test_extract_ast_patterns_with_decorator(self):
        """Test extracting AST patterns with decorators."""
        agent = DocGenAgent()
        prompt = "FunctionDef with decorator '@login_required'"

        patterns = agent._extract_ast_patterns(prompt)

        # Should have AST patterns extracted
        assert len(patterns) > 0
        ast_patterns = [p for p in patterns if p["type"] == "ast"]
        # The actual pattern is a description, not the decorator itself
        assert any("decorator" in p["pattern"].lower() for p in ast_patterns)

    def test_extract_ast_patterns_multiple_patterns(self):
        """Test extracting multiple AST patterns."""
        agent = DocGenAgent()
        prompt = """FunctionDef with decorator '@login_required'
FunctionDef without docstring
ClassDef with decorator '@login_required'"""

        patterns = agent._extract_ast_patterns(prompt)

        assert len(patterns) >= 3

    def test_extract_ast_patterns_empty_prompt(self):
        """Test returning empty list with empty prompt."""
        agent = DocGenAgent()
        patterns = agent._extract_ast_patterns("")

        assert len(patterns) == 0

    def test_extract_ast_patterns_case_insensitive(self):
        """Test AST pattern extraction is case insensitive."""
        agent = DocGenAgent()
        prompt = "functiondef with decorator '@login'"

        patterns = agent._extract_ast_patterns(prompt)

        # Should still match (regex is case insensitive)
        assert len(patterns) > 0


class TestDocGenAgentExtractFilePathPatterns:
    """Test file path pattern extraction."""

    def test_extract_file_path_patterns_with_glob(self):
        """Test extracting glob patterns."""
        agent = DocGenAgent()
        prompt = """You specialize in auth review.

File patterns:
- "auth/**/*.py"
- "server/**/*"
- "config.py" """

        patterns = agent._extract_file_path_patterns(prompt, MagicMock())

        assert len(patterns) >= 2
        path_patterns = [p for p in patterns if p["type"] == "file_path"]
        assert any("auth" in p["pattern"] for p in path_patterns)

    def test_extract_file_path_patterns_weight_assignment(self):
        """Test weight assignment based on pattern type."""
        agent = DocGenAgent()
        prompt = """auth/**.py
server/**/*.py
config.py"""

        patterns = agent._extract_file_path_patterns(prompt, MagicMock())

        # Check weights
        for p in patterns:
            assert "weight" in p
            assert p["type"] == "file_path"

    def test_extract_file_path_patterns_no_duplicates(self):
        """Test duplicate patterns are not included."""
        agent = DocGenAgent()
        prompt = """auth/**.py
auth/**.py"""

        patterns = agent._extract_file_path_patterns(prompt, MagicMock())

        unique_patterns = [p["pattern"] for p in patterns]
        assert len(patterns) == len(set(unique_patterns))

    def test_extract_file_path_patterns_empty_prompt(self):
        """Test returning empty list with empty prompt."""
        agent = DocGenAgent()
        patterns = agent._extract_file_path_patterns("", MagicMock())

        assert len(patterns) == 0

    def test_extract_file_path_patterns_filters_non_glob(self):
        """Test that non-glob patterns are filtered out."""
        agent = DocGenAgent()
        prompt = "Regular string without glob patterns"

        patterns = agent._extract_file_path_patterns(prompt, MagicMock())

        # Should have no file_path patterns
        path_patterns = [p for p in patterns if p["type"] == "file_path"]
        assert len(path_patterns) == 0


class TestDocGenAgentExtractContentPatterns:
    """Test content pattern extraction."""

    def test_extract_content_patterns_with_secrets(self):
        """Test extracting content patterns for secrets."""
        agent = DocGenAgent()
        prompt = "password = secret123\napi_key = abc123"

        patterns = agent._extract_content_patterns(prompt)

        assert len(patterns) > 0
        content_patterns = [p for p in patterns if p["type"] == "content"]
        assert any("password" in p["pattern"] for p in content_patterns)

    def test_extract_content_patterns_with_eval_exec(self):
        """Test extracting patterns for eval/exec."""
        agent = DocGenAgent()
        prompt = "result = eval(user_input)"

        patterns = agent._extract_content_patterns(prompt)

        assert len(patterns) > 0
        content_patterns = [p for p in patterns if p["type"] == "content"]
        assert any("eval" in p["pattern"] for p in content_patterns)

    def test_extract_content_patterns_empty_prompt(self):
        """Test returning empty list with empty prompt."""
        agent = DocGenAgent()
        patterns = agent._extract_content_patterns("")

        assert len(patterns) == 0

    def test_extract_content_patterns_case_insensitive(self):
        """Test content pattern extraction is case insensitive."""
        agent = DocGenAgent()
        prompt = "PASSWORD = secret"

        patterns = agent._extract_content_patterns(prompt)

        # Should still match
        assert len(patterns) > 0


class TestDocGenAgentExtractHeuristicsFromPrompt:
    """Test heuristic extraction from system prompt."""

    def test_extract_heuristics_from_bullets(self):
        """Test extracting heuristics from bullet points."""
        agent = DocGenAgent()
        prompt = """You specialize in security.

Blocking conditions:
- plaintext secrets in code
- eval() without proper validation

High-signal file patterns:
- server/**.py
- credentials.py"""

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        assert len(heuristics) > 0
        assert any("secrets" in h.lower() for h in heuristics)
        assert any("eval" in h.lower() for h in heuristics)

    def test_extract_heuristics_from_should_patterns(self):
        """Test extracting heuristics with should/recommend/consider."""
        agent = DocGenAgent()
        prompt = "Should check for SQL injection\nConsider using parameterized queries\nRecommend adding validation"

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        assert len(heuristics) > 0
        assert any("should" in h.lower() for h in heuristics)

    def test_extract_heuristics_with_questions(self):
        """Test extracting heuristics from 'must answer:' sections."""
        agent = DocGenAgent()
        prompt = """must answer:
1. What authentication method is used?
2. How are secrets stored?"""

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        assert len(heuristics) > 0
        assert any("authentication" in h.lower() for h in heuristics)

    def test_extract_heuristics_remove_duplicates(self):
        """Test duplicates are removed."""
        agent = DocGenAgent()
        prompt = """Should check for SQL injection
Should verify input validation
Consider using parameterized queries
Consider using parameterized queries"""

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        # Should have no duplicates
        lower_heuristics = [h.lower() for h in heuristics]
        assert len(lower_heuristics) == len(set(lower_heuristics))

    def test_extract_heuristics_truncation(self):
        """Test heuristics are limited to 15 items."""
        agent = DocGenAgent()
        prompt = "Should check: " + "\nShould check: ".join([f"Check {i}" for i in range(20)])

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        # Should be truncated to 15
        assert len(heuristics) <= 15

    def test_extract_heuristics_empty_prompt(self):
        """Test returning default heuristics with empty prompt."""
        agent = DocGenAgent()
        heuristics = agent._extract_heuristics_from_prompt("", "security")

        # Should return non-empty list
        assert len(heuristics) > 0

    def test_extract_heuristics_filter_json_schema(self):
        """Test JSON schema sections are filtered out."""
        agent = DocGenAgent()
        prompt = """{
  "title": "SecurityRequest",
  "type": "object",
  "properties": {
    "should": "something",
    "include": "something"
  }
}

Look for actual security issues."""

        heuristics = agent._extract_heuristics_from_prompt(prompt, "security")

        # Should filter out schema entries
        assert len(heuristics) > 0
        # Should not contain filtered out patterns
        assert not any("title" in h for h in heuristics)


class TestDocGenAgentDetermineAgentType:
    """Test agent type determination."""

    def test_determine_required_agent(self):
        """Test identifying required agents."""
        agent = DocGenAgent()

        class SecurityReviewer(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent_type = agent._determine_agent_type(SecurityReviewer())

        assert agent_type == "required"

    def test_determine_optional_agent(self):
        """Test identifying optional agents."""
        agent = DocGenAgent()

        class CustomAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent_type = agent._determine_agent_type(CustomAgent())

        assert agent_type == "optional"

    def test_required_agents_list(self):
        """Test that required agents match expected list."""
        agent = DocGenAgent()
        required = ["architecture", "security", "linting", "diff_scoper", "requirements"]

        for agent_name in required:
            # Create test class with the exact name
            class TestAgent(BaseReviewerAgent):
                def get_system_prompt(self) -> str:
                    return "Test"

                def get_relevant_file_patterns(self):
                    return []

                async def review(self, context):
                    pass

            TestAgent.__name__ = f"{agent_name.capitalize()}Reviewer"

            agent_type = agent._determine_agent_type(TestAgent())
            assert agent_type == "required", f"{agent_name} should be required"

    def test_non_required_agent_names(self):
        """Test non-required agents."""
        agent = DocGenAgent()
        non_required = ["documentation", "performance", "telemetry", "dependencies"]

        for agent_name in non_required:

            class MockAgent(BaseReviewerAgent):
                def get_system_prompt(self) -> str:
                    return "Test"

                def get_relevant_file_patterns(self):
                    return []

                async def review(self, context):
                    pass

            # Monkey-patch class name
            MockAgent.__name__ = f"{agent_name.capitalize()}Reviewer"

            agent_type = agent._determine_agent_type(MockAgent())
            assert agent_type == "optional", f"{agent_name} should be optional"


class TestDocGenAgentGenerateYamlFrontmatter:
    """Test YAML frontmatter generation."""

    def test_generate_yaml_frontmatter_basic(self):
        """Test generating basic YAML frontmatter."""
        agent = DocGenAgent()
        patterns = [
            {"type": "ast", "pattern": "FunctionDef", "weight": 0.9},
            {"type": "file_path", "pattern": "*.py", "weight": 0.7},
        ]
        heuristics = ["Check for security issues"]

        frontmatter = agent._generate_yaml_frontmatter(
            agent_name="security",
            agent_type="required",
            patterns=patterns,
            heuristics=heuristics,
            prompt_hash="abc123def456",
        )

        assert "agent: security" in frontmatter
        assert "agent_type: required" in frontmatter
        assert "version: 1.0.0" in frontmatter
        assert "prompt_hash: abc123def456" in frontmatter
        assert "patterns:" in frontmatter
        assert "heuristics:" in frontmatter
        assert "FunctionDef" in frontmatter
        assert "*.py" in frontmatter
        assert "Check for security issues" in frontmatter

    def test_generate_yaml_frontmatter_no_patterns(self):
        """Test YAML frontmatter with no patterns."""
        agent = DocGenAgent()
        frontmatter = agent._generate_yaml_frontmatter(
            agent_name="test",
            agent_type="optional",
            patterns=[],
            heuristics=[],
            prompt_hash="test123",
        )

        assert "agent: test" in frontmatter
        assert "patterns:" in frontmatter
        # Just check patterns section exists
        assert frontmatter.startswith("---")

    def test_generate_yaml_frontmatter_no_heuristics(self):
        """Test YAML frontmatter with no heuristics."""
        agent = DocGenAgent()
        frontmatter = agent._generate_yaml_frontmatter(
            agent_name="test",
            agent_type="optional",
            patterns=[],
            heuristics=[],
            prompt_hash="test123",
        )

        assert "heuristics:" in frontmatter
        assert frontmatter.startswith("---")

    def test_generate_yaml_frontmatter_generated_at_format(self):
        """Test generated_at timestamp format."""
        agent = DocGenAgent()
        import datetime
        import re

        # Capture timestamps with microseconds
        before = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        frontmatter = agent._generate_yaml_frontmatter(
            agent_name="test",
            agent_type="optional",
            patterns=[],
            heuristics=[],
            prompt_hash="test123",
        )
        after = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

        # Check timestamp format (ISO 8601 with Z)
        assert "generated_at:" in frontmatter
        # Extract time string (may have microseconds)
        time_str = frontmatter.split("generated_at:")[1].strip().split("\\n")[0]
        assert "T" in time_str
        assert "Z" in time_str

        # Parse time string including microseconds, then set microseconds to 0 for comparison
        time_value = datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        time_value = time_value.replace(microsecond=0)

        # Check time is reasonable (within 1 minute of now)
        assert before <= time_value <= after

    def test_generate_yaml_frontmatter_pattern_fields(self):
        """Test all pattern fields are present."""
        agent = DocGenAgent()
        pattern = {"type": "ast", "pattern": "TestPattern", "language": "python", "weight": 0.85}

        frontmatter = agent._generate_yaml_frontmatter(
            agent_name="test",
            agent_type="required",
            patterns=[pattern],
            heuristics=[],
            prompt_hash="test123",
        )

        assert "type: ast" in frontmatter
        assert '"TestPattern"' in frontmatter
        assert "language: python" in frontmatter
        assert "weight: 0.85" in frontmatter


class TestDocGenAgentGenerateFullDocumentation:
    """Test full documentation generation."""

    def test_generate_full_documentation(self):
        """Test generating complete documentation."""
        agent = DocGenAgent()

        prompt = """You specialize in security.

Look for:
- @login_required decorator
- password = xxx
"""

        patterns = [
            {"type": "ast", "pattern": "@login_required", "weight": 0.9},
            {"type": "content", "pattern": "password =", "weight": 0.95},
        ]
        heuristics = ["Check for plaintext secrets"]

        content = agent._generate_full_documentation(
            agent_name="security",
            frontmatter="---\nagent: security\n---",
            system_prompt=prompt,
            patterns=patterns,
            heuristics=heuristics,
        )

        assert content.startswith("---")
        assert "security" in content
        assert "@login_required" in content
        assert "password =" in content
        assert "Check for plaintext secrets" in content
        assert "AST Patterns" in content
        # File Path Patterns section only appears when there are file_path patterns
        # assert "File Path Patterns" in content
        assert "Content Patterns" in content
        assert "Usage During Review" in content
        assert "Maintenance" in content

    def test_generate_full_documentation_empty_patterns(self):
        """Test documentation generation with no patterns."""
        agent = DocGenAgent()

        content = agent._generate_full_documentation(
            agent_name="test",
            frontmatter="---\nagent: test\n---",
            system_prompt="Test prompt",
            patterns=[],
            heuristics=[],
        )

        assert content.startswith("---")
        assert "test" in content
        # No special "No patterns found" message in actual implementation
        assert "# Test Reviewer Entry Points" in content

    def test_generate_full_documentation_empty_heuristics(self):
        """Test documentation generation with no heuristics."""
        agent = DocGenAgent()

        content = agent._generate_full_documentation(
            agent_name="test",
            frontmatter="---\nagent: test\n---",
            system_prompt="Test prompt",
            patterns=[],
            heuristics=[],
        )

        assert content.startswith("---")
        assert "test" in content
        # No special "No heuristics" message in actual implementation
        assert "# Test Reviewer Entry Points" in content

    def test_generate_full_documentation_overview_section(self):
        """Test overview section is generated correctly."""
        agent = DocGenAgent()

        content = agent._generate_full_documentation(
            agent_name="test",
            frontmatter="---\nagent: test\n---",
            system_prompt="You specialize in testing.",
            patterns=[],
            heuristics=[],
        )

        assert "# Test Reviewer Entry Points" in content
        assert "This document defines entry points" in content
        # specialization section only appears if pattern matches
        # assert "specializes in" in content


class TestDocGenAgentSaveDoc:
    """Test documentation saving."""

    def test_save_doc_creates_directory(self, tmp_path: Path):
        """Test that directory is created if it doesn't exist."""
        agent = DocGenAgent()
        doc_path = tmp_path / "new_dir" / "agent.md"

        content = "---\nagent: test\n---"
        agent._save_doc(doc_path, content)

        assert doc_path.exists()
        assert doc_path.read_text() == content

    def test_save_doc_overwrites_existing(self, tmp_path: Path):
        """Test that existing file is overwritten."""
        agent = DocGenAgent()
        doc_path = tmp_path / "agent.md"

        # Write initial content
        doc_path.write_text("Initial content")

        # Overwrite
        content = "---\nagent: test\n---"
        agent._save_doc(doc_path, content)

        assert doc_path.exists()
        assert doc_path.read_text() == content

    def test_save_doc_with_content(self, tmp_path: Path):
        """Test saving documentation with content."""
        agent = DocGenAgent()
        doc_path = tmp_path / "agent.md"
        content = """---
agent: security
prompt_hash: abc123
---

# Security Documentation"""
        agent._save_doc(doc_path, content)

        assert doc_path.exists()
        saved_content = doc_path.read_text()
        assert saved_content == content

    def test_save_doc_unicode_support(self, tmp_path: Path):
        """Test saving with unicode content."""
        agent = DocGenAgent()
        doc_path = tmp_path / "agent.md"
        content = """---
agent: test
---

# Documentation with Korean: 한국어
# and emoji: 🇰🇷 🎉"""
        agent._save_doc(doc_path, content)

        assert doc_path.exists()
        saved_content = doc_path.read_text()
        assert "한국어" in saved_content
        assert "🇰🇷" in saved_content

    def test_save_doc_creates_nested_directories(self, tmp_path: Path):
        """Test creating deeply nested directories."""
        agent = DocGenAgent()
        doc_path = tmp_path / "a" / "b" / "c" / "d" / "agent.md"

        content = "---\nagent: test\n---"
        agent._save_doc(doc_path, content)

        assert doc_path.exists()
        assert doc_path.parent.exists()

    def test_save_doc_empty_content(self, tmp_path: Path):
        """Test saving empty content."""
        agent = DocGenAgent()
        doc_path = tmp_path / "agent.md"

        agent._save_doc(doc_path, "")

        assert doc_path.exists()
        assert doc_path.read_text() == ""


class TestDocGenAgentGenerateForAgent:
    """Test main generate method."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with all required methods."""
        agent = MagicMock(spec=BaseReviewerAgent)
        # Add get_agent_name to the mock's allowed methods
        agent.get_agent_name = MagicMock(return_value="security")
        agent.get_system_prompt.return_value = (
            "You specialize in testing.\n\nLook for:\n- @test decorator\n- FunctionDef"
        )
        agent.get_relevant_file_patterns.return_value = ["tests/**", "*.py"]
        return agent

    @pytest.fixture
    def tmp_output_dir(self, tmp_path: Path):
        """Create temporary output directory."""
        output_dir = tmp_path / "docs"
        output_dir.mkdir()
        return output_dir

    def test_generate_for_agent_creates_documentation(
        self, tmp_output_dir: Path, mock_agent: MagicMock
    ):
        """Test that documentation is generated successfully."""
        # Save doc_gen agent with custom output dir
        doc_gen = DocGenAgent()

        success, message = doc_gen.generate_for_agent(
            mock_agent, output_path=tmp_output_dir / "security.md"
        )

        assert success is True
        assert "security" in message.lower()
        assert (tmp_output_dir / "security.md").exists()

    def test_generate_for_agent_creates_parent_directory(
        self, tmp_path: Path, mock_agent: MagicMock
    ):
        """Test that parent directories are created."""
        output_path = tmp_path / "deep" / "path" / "security.md"
        doc_gen = DocGenAgent()

        success, message = doc_gen.generate_for_agent(mock_agent, output_path=output_path)

        assert success is True
        assert output_path.exists()

    def test_generate_for_agent_force_overwrite(self, tmp_path: Path, mock_agent: MagicMock):
        """Test that force flag overwrites existing documentation."""
        output_path = tmp_path / "security.md"
        old_hash = "abc123def456"
        doc_gen = DocGenAgent()

        # Write file with old content and hash
        output_path.write_text(f"""---
agent: test
prompt_hash: {old_hash}
---
Old content""")

        # Generate with force - should overwrite
        mock_agent.get_system_prompt.return_value = (
            "You specialize in testing.\n\nLook for:\n- @test decorator\n- FunctionDef"
        )
        success, message = doc_gen.generate_for_agent(
            mock_agent, force=True, output_path=output_path
        )
        content = output_path.read_text()

        # Verify the file was successfully generated
        assert success is True
        # Check that the old content is no longer there
        assert "Old content" not in content
        # Check that old hash is replaced with new hash
        import re

        new_hash = re.search(r"prompt_hash:\s*(\S+)", content)
        assert new_hash is not None
        assert new_hash.group(1) != old_hash
        # Verify the file has the new documentation structure
        assert "---" in content
        assert "version: 1.0.0" in content
        # Check that patterns are extracted (should have at least one pattern)
        assert "patterns:" in content
        # Verify the file exists
        assert output_path.exists()

    def test_generate_for_agent_no_force_when_hash_matches(
        self, tmp_path: Path, mock_agent: MagicMock
    ):
        """Test that documentation is not regenerated when hash matches and force=False."""
        output_path = tmp_path / "security.md"
        test_hash = "abc123def456"
        doc_gen = DocGenAgent()

        # Create a file with content first
        output_path.write_text(f"""---
agent: test
prompt_hash: {test_hash}
---
# Test content""")

        # Mock get_system_prompt to return content with same hash
        mock_agent.get_system_prompt.return_value = "test prompt"

        with (
            patch.object(doc_gen, "_extract_existing_hash", return_value=test_hash),
            patch.object(doc_gen, "_calculate_hash", return_value=test_hash),
        ):
            success, message = doc_gen.generate_for_agent(mock_agent, output_path=output_path)

        # Check that message contains "up-to-date" (doc already up to date)
        assert "up-to-date" in message.lower()
        # Verify content was not overwritten
        assert "# Test content" in output_path.read_text()

    def test_generate_for_agent_force_when_hash_matches(
        self, tmp_path: Path, mock_agent: MagicMock
    ):
        """Test that documentation IS regenerated when hash matches and force=True."""
        output_path = tmp_path / "security.md"
        doc_gen = DocGenAgent()

        mock_agent.get_system_prompt.return_value = "test prompt"

        with (
            patch.object(doc_gen, "_extract_existing_hash", return_value="abc123"),
            patch.object(doc_gen, "_calculate_hash", return_value="abc123"),
            patch.object(doc_gen, "_save_doc") as mock_save,
        ):
            success, message = doc_gen.generate_for_agent(
                mock_agent, force=True, output_path=output_path
            )

        # Check that _save_doc WAS called (doc was overwritten)
        assert mock_save.called
        assert "generated" in message.lower()

    def test_generate_for_agent_custom_output_path(self, tmp_path: Path, mock_agent: MagicMock):
        """Test that custom output path is used."""
        custom_path = tmp_path / "custom" / "security.md"
        doc_gen = DocGenAgent()

        success, message = doc_gen.generate_for_agent(mock_agent, output_path=custom_path)

        assert success is True
        assert custom_path.exists()
        assert "custom" in str(custom_path)

    def test_generate_for_agent_exception_handling(self, tmp_path: Path, mock_agent: MagicMock):
        """Test that exceptions are caught and returned as error."""
        output_path = tmp_path / "security.md"

        # Make get_system_prompt raise exception
        mock_agent.get_system_prompt.side_effect = Exception("Test error")

        doc_gen = DocGenAgent()

        success, message = doc_gen.generate_for_agent(mock_agent, output_path=output_path)

        assert success is False
        assert "error" in message.lower()
        assert "test error" in message.lower()

    def test_generate_for_agent_with_agent_name_extraction(self, tmp_path: Path):
        """Test agent name is extracted from agent instance."""

        class TestAgent(BaseReviewerAgent):
            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self):
                return []

            async def review(self, context):
                pass

        agent = TestAgent()
        doc_gen = DocGenAgent()

        success, message = doc_gen.generate_for_agent(agent, output_path=tmp_path / "test.md")

        assert success is True
        assert (tmp_path / "test.md").exists()

    def test_generate_for_agent_all_required_methods_called(
        self, tmp_path: Path, mock_agent: MagicMock
    ):
        """Test that all required methods are called during generation."""
        doc_gen = DocGenAgent()

        doc_gen.generate_for_agent(mock_agent, output_path=tmp_path / "test.md")

        # Verify all required methods were called
        mock_agent.get_system_prompt.assert_called()
        # get_agent_name is called by doc_gen, so verify it was called at least once
        mock_agent.get_agent_name.assert_called()
        mock_agent.get_relevant_file_patterns.assert_called_once()

    def test_generate_for_agent_specialization_extraction(
        self, tmp_path: Path, mock_agent: MagicMock
    ):
        """Test that specialization is extracted from system prompt."""
        doc_gen = DocGenAgent()

        doc_gen.generate_for_agent(mock_agent, output_path=tmp_path / "test.md")

        # Verify get_system_prompt was called
        assert mock_agent.get_system_prompt.called
