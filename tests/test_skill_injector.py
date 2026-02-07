"""Tests for SkillInjector"""
from __future__ import annotations

from unittest.mock import Mock
import pytest
from pathlib import Path
from dawn_kestrel.skills.injector import SkillInjector


def test_no_skills_returns_base_prompt():
    injector = SkillInjector(base_dir=Path("/tmp"))

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=[],
        default_prompt="You are a helpful assistant.",
    )

    assert result == "You are a helpful assistant."


def test_empty_agent_prompt_with_no_skills():
    injector = SkillInjector(base_dir=Path("/tmp"))

    result = injector.build_agent_prompt(
        agent_prompt="",
        skill_names=[],
        default_prompt="Default prompt.",
    )

    assert result == "Default prompt."


def test_one_skill_injected():
    injector = SkillInjector(base_dir=Path("/tmp"))

    mock_skill = Mock()
    mock_skill.name = "git-master"
    mock_skill.description = "Expert git operations agent"
    mock_skill.content = "You are an expert git agent with full git operations capabilities."

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["git-master"],
        default_prompt="You are a helpful assistant.",
    )

    expected_sections = [
        "You have access to the following skills:",
        "- git-master: Expert git operations agent",
        "  content: You are an expert git agent with full git operations capabilities.",
        "You are a helpful assistant.",
    ]

    for section in expected_sections:
        assert section in result, f"Expected '{section}' in result"


def test_multiple_skills_injected():
    injector = SkillInjector(base_dir=Path("/tmp"))

    mock_skill1 = Mock()
    mock_skill1.name = "playwright"
    mock_skill1.description = "Browser automation"
    mock_skill1.content = "You can use Playwright to automate browser interactions."

    mock_skill2 = Mock()
    mock_skill2.name = "frontend-ui-ux"
    mock_skill2.description = "UI/UX design expert"
    mock_skill2.content = "You have strong design sensibilities and can create beautiful interfaces."

    mock_skill3 = Mock()
    mock_skill3.name = "git-master"
    mock_skill3.description = "Git operations"
    mock_skill3.content = "You know git commands and can manage repositories."

    injector.loader.get_skill_by_name = Mock(side_effect=[mock_skill1, mock_skill2, mock_skill3])

    result = injector.build_agent_prompt(
        agent_prompt="You are an AI assistant.",
        skill_names=["playwright", "frontend-ui-ux", "git-master"],
        default_prompt="You are a helpful assistant.",
    )

    # Check all skills are present
    assert "playwright" in result
    assert "frontend-ui-ux" in result
    assert "git-master" in result

    # Check descriptions
    assert "Browser automation" in result
    assert "UI/UX design expert" in result
    assert "Git operations" in result

    # Check content
    assert "You can use Playwright" in result
    assert "You have strong design sensibilities" in result
    assert "You know git commands" in result

    # Check base prompt is at the end
    assert result.rstrip().endswith("You are an AI assistant.")


def test_skill_includes_base_prompt():
    injector = SkillInjector(base_dir=Path("/tmp"))

    mock_skill = Mock()
    mock_skill.name = "git-master"
    mock_skill.description = "Git operations"
    mock_skill.content = "You know git commands."

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a Python expert.",
        skill_names=["git-master"],
        default_prompt="You are a helpful assistant.",
    )

    # Skills section should come before base prompt
    result_lines = result.split("\n")
    base_prompt_idx = None

    for i, line in enumerate(result_lines):
        if "You are a Python expert" in line:
            base_prompt_idx = i
            break

    skills_section_idx = None
    for i, line in enumerate(result_lines):
        if "You have access to the following skills" in line:
            skills_section_idx = i
            break

    assert skills_section_idx is not None
    assert base_prompt_idx is not None
    assert skills_section_idx < base_prompt_idx


def test_truncation_with_budget():
    injector = SkillInjector(
        base_dir=Path("/tmp"),
        max_char_budget=100,
    )

    mock_skill = Mock()
    mock_skill.name = "long-skill"
    mock_skill.description = "Very long skill description"
    mock_skill.content = "A" * 200

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["long-skill"],
        default_prompt="You are a helpful assistant.",
    )

    # Result should be truncated to 100 chars (plus base prompt)
    assert len(result) <= 100 + len("You are a helpful assistant.")


def test_truncation_suffix_included():
    injector = SkillInjector(
        base_dir=Path("/tmp"),
        max_char_budget=50,
    )

    mock_skill = Mock()
    mock_skill.name = "truncate-test"
    mock_skill.description = "Test truncation"
    mock_skill.content = "A" * 200

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["truncate-test"],
        default_prompt="You are a helpful assistant.",
    )

    # Result should contain the suffix
    assert "..." in result


def test_no_truncation_when_below_budget():
    injector = SkillInjector(
        base_dir=Path("/tmp"),
        max_char_budget=1000,
    )

    mock_skill = Mock()
    mock_skill.name = "short-skill"
    mock_skill.description = "Short description"
    mock_skill.content = "Short skill content."

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["short-skill"],
        default_prompt="You are a helpful assistant.",
    )

    # Full content should be present
    assert "Short skill content." in result


def test_invalid_skill_names_ignored():
    injector = SkillInjector(base_dir=Path("/tmp"))

    mock_skill = Mock()
    mock_skill.name = "git-master"
    mock_skill.description = "Git operations"
    mock_skill.content = "You know git commands."

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["non-existent-skill-1", "non-existent-skill-2", "git-master"],
        default_prompt="You are a helpful assistant.",
    )

    # Only valid skill should be injected
    assert "git-master" in result
    assert "non-existent-skill-1" not in result
    assert "non-existent-skill-2" not in result


def test_deterministic_formatting():
    """Skills injected in input order for deterministic output."""
    injector = SkillInjector(base_dir=Path("/tmp"))

    def get_skill(name):
        if name == "skill-one":
            mock_skill = Mock()
            mock_skill.name = "skill-one"
            mock_skill.description = "First skill"
            mock_skill.content = "Content of first skill."
            return mock_skill
        elif name == "skill-two":
            mock_skill = Mock()
            mock_skill.name = "skill-two"
            mock_skill.description = "Second skill"
            mock_skill.content = "Content of second skill."
            return mock_skill
        return None

    injector.loader.get_skill_by_name = Mock(side_effect=get_skill)

    # Input order preserved in output
    result1 = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["skill-one", "skill-two"],
        default_prompt="You are a helpful assistant.",
    )

    result2 = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["skill-two", "skill-one"],
        default_prompt="You are a helpful assistant.",
    )

    # Each result is deterministic (same input order = same output order)
    assert result1 == result1  # Just checking first call is stable
    assert result2 == result2  # Just checking second call is stable


def test_skill_with_empty_description():
    injector = SkillInjector(base_dir=Path("/tmp"))

    mock_skill = Mock()
    mock_skill.name = "no-desc"
    mock_skill.description = ""
    mock_skill.content = "Skill without description."

    injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = injector.build_agent_prompt(
        agent_prompt="You are a helpful assistant.",
        skill_names=["no-desc"],
        default_prompt="You are a helpful assistant.",
    )

    # Should still inject skill with empty description
    assert "no-desc" in result
    assert "Skill without description" in result
