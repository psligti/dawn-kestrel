"""Tests for skills module - models, registry, contracts, and blocking"""
import pytest
import asyncio

from opencode_python.skills.models import Skill, SkillState
from opencode_python.skills.contracts import (
    SkillContract,
    PlanningOutput,
    RefactorOutput,
    TestGenerationOutput,
    DocsOutput,
    PLANNING_CONTRACT,
)
from opencode_python.skills.registry import SkillRegistry
from opencode_python.skills.blocking import (
    SkillBlockingInterceptor,
    SkillExecutionDenied,
    setup_event_listeners,
)


class TestSkillModels:
    """Test Skill and SkillState models"""

    def test_skill_creation(self):
        """Test creating a Skill model"""
        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Test template: {task}",
            output_schema={"type": "object"},
            is_enabled_by_default=True,
            category="test",
        )

        assert skill.id == "test-skill"
        assert skill.name == "Test Skill"
        assert skill.description == "A test skill"
        assert skill.is_enabled_by_default is True
        assert skill.category == "test"

    def test_skill_state_creation(self):
        """Test creating a SkillState model"""
        state = SkillState(
            session_id="session-123",
            skill_id="test-skill",
            is_enabled=True,
            is_blocked=False,
        )

        assert state.session_id == "session-123"
        assert state.skill_id == "test-skill"
        assert state.is_enabled is True
        assert state.is_blocked is False
        assert state.use_count == 0
        assert state.last_used is None

    def test_skill_state_mark_used(self):
        """Test marking a skill as used"""
        state = SkillState(
            session_id="session-123",
            skill_id="test-skill",
            is_enabled=True,
            is_blocked=False,
        )

        state.mark_used()

        assert state.use_count == 1
        assert state.last_used is not None


class TestSkillContracts:
    """Test skill contracts and output schemas"""

    def test_planning_contract(self):
        """Test planning contract output schema"""
        assert PLANNING_CONTRACT.output_model == PlanningOutput
        assert "type" in PLANNING_CONTRACT.output_schema
        assert PLANNING_CONTRACT.output_schema["type"] == "object"

    def test_planning_output_validation(self):
        """Test PlanningOutput validation"""
        output = PlanningOutput(
            tasks=["task1", "task2"],
            dependencies={"task1": [], "task2": ["task1"]},
            priority={"task1": "high", "task2": "medium"},
            estimated_time={"task1": "1h", "task2": "30m"},
        )

        assert len(output.tasks) == 2
        assert "task1" in output.dependencies
        assert output.priority["task1"] == "high"

    def test_refactor_output_validation(self):
        """Test RefactorOutput validation"""
        output = RefactorOutput(
            changes=[
                {
                    "file": "test.py",
                    "line": 10,
                    "old_code": "old",
                    "new_code": "new",
                }
            ],
            improvements=["Remove code duplication"],
            warnings=["Breaking change detected"],
        )

        assert len(output.changes) == 1
        assert len(output.improvements) == 1
        assert len(output.warnings) == 1

    def test_test_generation_output_validation(self):
        """Test TestGenerationOutput validation"""
        output = TestGenerationOutput(
            test_files=[{"path": "test_example.py", "content": "def test_..."}],
            test_cases=[{"description": "Test case 1", "assertions": ["assert True"]}],
            coverage_analysis={"total": 100, "covered": 80},
        )

        assert len(output.test_files) == 1
        assert len(output.test_cases) == 1
        assert output.coverage_analysis["total"] == 100

    def test_docs_output_validation(self):
        """Test DocsOutput validation"""

        output = DocsOutput(
            updated_files=[{"path": "module.py", "changes": ["Add docstring"]}],
            new_docs=[{"path": "README.md", "content": "# Module"}],
            api_documentation={"module": {"func1": "Description"}},
        )

        assert len(output.updated_files) == 1
        assert len(output.new_docs) == 1
        assert "module" in output.api_documentation


class TestSkillRegistry:
    """Test skill registry functionality"""

    def setup_method(self):
        """Setup for each test - clear global registry"""
        from opencode_python.skills.registry import registry

        for skill_id in list(registry._skills.keys()):
            registry.unregister_skill(skill_id)

        for session_id in list(registry._session_states.keys()):
            registry.cleanup_session(session_id)

    def test_register_skill(self):
        """Test registering a skill"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)

        assert registry.get_skill("test-skill") is not None
        assert registry.get_skill("test-skill") == skill

    def test_unregister_skill(self):
        """Test unregistering a skill"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.unregister_skill("test-skill")

        assert registry.get_skill("test-skill") is None

    def test_enable_skill(self):
        """Test enabling a skill for a session"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        success = registry.enable_skill("session-123", "test-skill")

        assert success is True
        assert registry.is_skill_enabled("session-123", "test-skill") is True

    def test_disable_skill(self):
        """Test disabling a skill for a session"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")
        success = registry.disable_skill("session-123", "test-skill")

        assert success is True
        assert registry.is_skill_enabled("session-123", "test-skill") is False

    def test_block_skill(self):
        """Test blocking a skill for a session"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        success = registry.block_skill("session-123", "test-skill", "Safety violation")

        assert success is True
        assert registry.is_skill_blocked("session-123", "test-skill") is True

        state = registry.get_skill_state("session-123", "test-skill")
        assert state.block_reason == "Safety violation"

    def test_unblock_skill(self):
        """Test unblocking a skill for a session"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.block_skill("session-123", "test-skill", "Safety violation")
        success = registry.unblock_skill("session-123", "test-skill")

        assert success is True
        assert registry.is_skill_blocked("session-123", "test-skill") is False

    def test_get_enabled_skills(self):
        """Test getting enabled skills for a session"""
        from opencode_python.skills.registry import registry

        skill1 = Skill(
            id="skill1",
            name="Skill 1",
            description="Skill 1",
            prompt_template="Template",
            output_schema={"type": "object"},
            is_enabled_by_default=True,
        )

        skill2 = Skill(
            id="skill2",
            name="Skill 2",
            description="Skill 2",
            prompt_template="Template",
            output_schema={"type": "object"},
            is_enabled_by_default=False,
        )

        registry.register_skill(skill1)
        registry.register_skill(skill2)
        registry.initialize_session("session-123")

        enabled = registry.get_enabled_skills("session-123")

        assert len(enabled) == 1
        assert enabled[0].id == "skill1"

    def test_initialize_session(self):
        """Test initializing a session with default skill states"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
            is_enabled_by_default=True,
        )

        registry.register_skill(skill)
        registry.initialize_session("session-123")

        assert registry.is_skill_enabled("session-123", "test-skill") is True
        assert registry.is_skill_blocked("session-123", "test-skill") is False

    def test_cleanup_session(self):
        """Test cleaning up a session"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")
        registry.cleanup_session("session-123")

        assert registry.get_skill_state("session-123", "test-skill") is None

    def test_mark_skill_used(self):
        """Test marking a skill as used"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")
        registry.mark_skill_used("session-123", "test-skill")

        state = registry.get_skill_state("session-123", "test-skill")
        assert state.use_count == 1
        assert state.last_used is not None


class TestSkillBlockingInterceptor:
    """Test skill blocking interceptor"""

    def setup_method(self):
        """Setup for each test - clear global registry and create new interceptor"""
        from opencode_python.skills.registry import registry

        for skill_id in list(registry._skills.keys()):
            registry.unregister_skill(skill_id)

        for session_id in list(registry._session_states.keys()):
            registry.cleanup_session(session_id)

        self.interceptor = SkillBlockingInterceptor()

    def test_check_execution_allowed_enabled(self):
        """Test checking execution for enabled skill"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")

        result = asyncio.run(
            self.interceptor.check_execution_allowed("session-123", "test-skill")
        )

        assert result is True

    def test_check_execution_allowed_disabled(self):
        """Test checking execution for disabled skill"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.disable_skill("session-123", "test-skill")

        with pytest.raises(SkillExecutionDenied) as exc_info:
            asyncio.run(
                self.interceptor.check_execution_allowed("session-123", "test-skill")
            )

        assert "disabled" in str(exc_info.value)

    def test_check_execution_allowed_blocked(self):
        """Test checking execution for blocked skill"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.block_skill("session-123", "test-skill", "Safety violation")

        with pytest.raises(SkillExecutionDenied) as exc_info:
            asyncio.run(
                self.interceptor.check_execution_allowed("session-123", "test-skill")
            )

        assert "blocked" in str(exc_info.value)
        assert "Safety violation" in str(exc_info.value)

    def test_check_execution_allowed_not_found(self):
        """Test checking execution for non-existent skill"""
        with pytest.raises(SkillExecutionDenied) as exc_info:
            asyncio.run(
                self.interceptor.check_execution_allowed("session-123", "non-existent")
            )

        assert "not found" in str(exc_info.value)

    def test_custom_interceptor(self):
        """Test custom interceptor registration and execution"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")

        def custom_interceptor(session_id, skill_id, context):
            return context.get("allow", False)

        self.interceptor.register_interceptor("test-skill", custom_interceptor)

        with pytest.raises(SkillExecutionDenied):
            asyncio.run(
                self.interceptor.check_execution_allowed(
                    "session-123", "test-skill", {"allow": False}
                )
            )

        result = asyncio.run(
            self.interceptor.check_execution_allowed(
                "session-123", "test-skill", {"allow": True}
            )
        )
        assert result is True

    def test_unregister_interceptor(self):
        """Test unregistering a custom interceptor"""
        from opencode_python.skills.registry import registry

        skill = Skill(
            id="test-skill",
            name="Test Skill",
            description="A test skill",
            prompt_template="Template",
            output_schema={"type": "object"},
        )

        registry.register_skill(skill)
        registry.enable_skill("session-123", "test-skill")

        def custom_interceptor(session_id, skill_id, context):
            return False

        self.interceptor.register_interceptor("test-skill", custom_interceptor)
        self.interceptor.unregister_interceptor("test-skill")

        result = asyncio.run(
            self.interceptor.check_execution_allowed("session-123", "test-skill")
        )
        assert result is True
