"""Tests for agent profiles and prerequisite checking"""
import pytest

from opencode_python.agents import (
    AgentProfile,
    Prerequisite,
    get_default_profiles,
    get_profile_by_id,
    check_prerequisites,
)


class TestAgentProfile:
    """Test AgentProfile model"""

    def test_create_profile(self):
        profile = AgentProfile(
            id="test",
            name="Test Profile",
            description="Test description",
            default_temperature=0.5,
        )
        assert profile.id == "test"
        assert profile.name == "Test Profile"
        assert profile.description == "Test description"
        assert profile.default_temperature == 0.5

    def test_profile_with_requirements(self):
        profile = AgentProfile(
            id="test",
            name="Test Profile",
            description="Test description",
            required_skills=["skill1", "skill2"],
            required_tools=["tool1"],
            capabilities=["capability1"],
        )
        assert len(profile.required_skills) == 2
        assert len(profile.required_tools) == 1
        assert len(profile.capabilities) == 1


class TestDefaultProfiles:
    """Test default agent profiles"""

    def test_get_default_profiles(self):
        profiles = get_default_profiles()
        assert len(profiles) >= 3
        profile_ids = [p.id for p in profiles]
        assert "coder" in profile_ids
        assert "reviewer" in profile_ids
        assert "planner" in profile_ids

    def test_coder_profile(self):
        profile = get_profile_by_id("coder")
        assert profile is not None
        assert profile.name == "Coder"
        assert "code_generation" in profile.required_skills
        assert "read" in profile.required_tools
        assert profile.category == "development"

    def test_reviewer_profile(self):
        profile = get_profile_by_id("reviewer")
        assert profile is not None
        assert profile.name == "Reviewer"
        assert "code_review" in profile.required_skills
        assert profile.category == "quality"

    def test_planner_profile(self):
        profile = get_profile_by_id("planner")
        assert profile is not None
        assert profile.name == "Planner"
        assert "planning" in profile.required_skills
        assert profile.category == "planning"

    def test_get_profile_by_id(self):
        profile = get_profile_by_id("coder")
        assert profile is not None
        assert profile.id == "coder"

    def test_get_profile_by_id_not_found(self):
        profile = get_profile_by_id("nonexistent")
        assert profile is None


class TestPrerequisiteChecking:
    """Test prerequisite checking logic"""

    def test_all_prerequisites_satisfied(self):
        profile = get_profile_by_id("coder")
        result = check_prerequisites(
            profile,
            available_skills=["code_generation", "test_generation", "code_review"],
            available_tools=["read", "write", "bash", "grep"],
            available_providers=["anthropic", "openai"],
        )
        assert result["satisfied"] is True
        assert len(result["missing"]) == 0
        assert len(result["warnings"]) == 0

    def test_missing_skill(self):
        profile = get_profile_by_id("coder")
        result = check_prerequisites(
            profile,
            available_skills=["test_generation"],  # Missing code_generation, code_review
            available_tools=["read", "write", "bash", "grep"],
            available_providers=["anthropic"],
        )
        assert result["satisfied"] is False
        assert len(result["missing"]) == 2
        missing_types = [m.type for m in result["missing"]]
        assert "skill" in missing_types

    def test_missing_tool(self):
        profile = get_profile_by_id("coder")
        result = check_prerequisites(
            profile,
            available_skills=["code_generation", "test_generation", "code_review"],
            available_tools=["read"],  # Missing write, bash, grep
            available_providers=["anthropic"],
        )
        assert result["satisfied"] is False
        assert len(result["missing"]) == 3
        missing_types = [m.type for m in result["missing"]]
        assert "tool" in missing_types

    def test_has_prerequisites_method(self):
        profile = get_profile_by_id("coder")
        assert profile.has_prerequisites(
            available_skills=["code_generation", "test_generation", "code_review"],
            available_tools=["read", "write", "bash", "grep"],
            available_providers=["anthropic"],
        ) is True

        assert profile.has_prerequisites(
            available_skills=["code_generation"],
            available_tools=["read"],
            available_providers=[],
        ) is False

    def test_get_missing_prerequisites(self):
        profile = get_profile_by_id("coder")
        missing = profile.get_missing_prerequisites(
            available_skills=["code_generation"],
            available_tools=["read"],
            available_providers=[],
        )
        assert len(missing) > 0

        missing_ids = [m.id for m in missing]
        assert "test_generation" in missing_ids
        assert "write" in missing_ids
