"""Integration tests for Bolt Merlin agents with FSM attachments.

Tests verify that all 11 Bolt Merlin agents have properly configured
lifecycle and workflow FSMs attached, and that FSM state transitions work correctly.
"""

import pytest
from typing import Any

from dawn_kestrel.agents.bolt_merlin import (
    create_orchestrator_agent,
    create_master_orchestrator_agent,
    create_planner_agent,
    create_autonomous_worker_agent,
    create_consultant_agent,
    create_pre_planning_agent,
    create_plan_validator_agent,
    create_librarian_agent,
    create_explore_agent,
    create_frontend_ui_ux_skill,
    create_multimodal_looker_agent,
)


def _unwrap_agent_config(config: Any) -> Any:
    """Unwrap agent config if it's a Result object.

    Some agents return Ok(AgentConfig) while others return AgentConfig directly.
    This helper handles both cases.
    """
    if hasattr(config, "unwrap"):
        return config.unwrap()
    return config


class TestBoltMerlinAgentsWithFSM:
    """Test suite for Bolt Merlin agents with FSM integration."""

    # ========================================================================
    # FSM Attachment Tests - verify all agents have FSMs attached
    # ========================================================================

    def test_orchestrator_has_fsms(self):
        """Test that orchestrator agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_orchestrator_agent())
        assert hasattr(config, "lifecycle_fsm"), "Config should have lifecycle_fsm attribute"
        assert hasattr(config, "workflow_fsm"), "Config should have workflow_fsm attribute"
        assert config.lifecycle_fsm is not None, "orchestrator should have lifecycle FSM"
        assert config.workflow_fsm is not None, "orchestrator should have workflow FSM"

    def test_master_orchestrator_has_fsms(self):
        """Test that master_orchestrator agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_master_orchestrator_agent())
        assert config.lifecycle_fsm is not None, "master_orchestrator should have lifecycle FSM"
        assert config.workflow_fsm is not None, "master_orchestrator should have workflow FSM"

    def test_planner_has_fsms(self):
        """Test that planner agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_planner_agent())
        assert config.lifecycle_fsm is not None, "planner should have lifecycle FSM"
        assert config.workflow_fsm is not None, "planner should have workflow FSM"

    def test_autonomous_worker_has_fsms(self):
        """Test that autonomous_worker agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_autonomous_worker_agent())
        assert config.lifecycle_fsm is not None, "autonomous_worker should have lifecycle FSM"
        assert config.workflow_fsm is not None, "autonomous_worker should have workflow FSM"

    def test_consultant_has_fsms(self):
        """Test that consultant agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_consultant_agent())
        assert config.lifecycle_fsm is not None, "consultant should have lifecycle FSM"
        assert config.workflow_fsm is not None, "consultant should have workflow FSM"

    def test_pre_planning_has_fsms(self):
        """Test that pre_planning agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_pre_planning_agent())
        assert config.lifecycle_fsm is not None, "pre_planning should have lifecycle FSM"
        assert config.workflow_fsm is not None, "pre_planning should have workflow FSM"

    def test_plan_validator_has_fsms(self):
        """Test that plan_validator agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_plan_validator_agent())
        assert config.lifecycle_fsm is not None, "plan_validator should have lifecycle FSM"
        assert config.workflow_fsm is not None, "plan_validator should have workflow FSM"

    def test_librarian_has_fsms(self):
        """Test that librarian agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_librarian_agent())
        assert config.lifecycle_fsm is not None, "librarian should have lifecycle FSM"
        assert config.workflow_fsm is not None, "librarian should have workflow FSM"

    def test_explore_has_fsms(self):
        """Test that explore agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_explore_agent())
        assert config.lifecycle_fsm is not None, "explore should have lifecycle FSM"
        assert config.workflow_fsm is not None, "explore should have workflow FSM"

    def test_frontend_ui_ux_has_fsms(self):
        """Test that frontend_ui_engineer agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_frontend_ui_ux_skill())
        assert config.lifecycle_fsm is not None, "frontend_ui_engineer should have lifecycle FSM"
        assert config.workflow_fsm is not None, "frontend_ui_engineer should have workflow FSM"

    def test_multimodal_looker_has_fsms(self):
        """Test that multimodal_looker agent has lifecycle and workflow FSMs."""
        config = _unwrap_agent_config(create_multimodal_looker_agent())
        assert config.lifecycle_fsm is not None, "multimodal_looker should have lifecycle FSM"
        assert config.workflow_fsm is not None, "multimodal_looker should have workflow FSM"

    # ========================================================================
    # Lifecycle FSM Transition Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_lifecycle_fsm_idle_to_running_to_completed(self):
        """Test lifecycle FSM successful transition: idle → running → completed."""
        config = _unwrap_agent_config(create_orchestrator_agent())
        fsm = config.lifecycle_fsm

        # Verify initial state
        state = await fsm.get_state()
        assert state == "idle", "FSM should start in idle state"

        # Transition to running
        result = await fsm.transition_to("running")
        assert result.is_ok(), f"Transition to running should succeed: {result}"

        state = await fsm.get_state()
        assert state == "running", "FSM should be in running state"

        # Transition to completed
        result = await fsm.transition_to("completed")
        assert result.is_ok(), f"Transition to completed should succeed: {result}"

        state = await fsm.get_state()
        assert state == "completed", "FSM should be in completed state"

    @pytest.mark.asyncio
    async def test_lifecycle_fsm_idle_to_running_to_failed(self):
        """Test lifecycle FSM failure transition: idle → running → failed."""
        config = _unwrap_agent_config(create_explore_agent())
        fsm = config.lifecycle_fsm

        # Verify initial state
        state = await fsm.get_state()
        assert state == "idle", "FSM should start in idle state"

        # Transition to running
        result = await fsm.transition_to("running")
        assert result.is_ok(), f"Transition to running should succeed: {result}"

        state = await fsm.get_state()
        assert state == "running", "FSM should be in running state"

        # Transition to failed
        result = await fsm.transition_to("failed")
        assert result.is_ok(), f"Transition to failed should succeed: {result}"

        state = await fsm.get_state()
        assert state == "failed", "FSM should be in failed state"

    @pytest.mark.asyncio
    async def test_lifecycle_fsm_pause_and_resume(self):
        """Test lifecycle FSM pause and resume: idle → running → paused → running."""
        config = _unwrap_agent_config(create_planner_agent())
        fsm = config.lifecycle_fsm

        # Navigate to running
        await fsm.transition_to("running")
        assert await fsm.get_state() == "running"

        # Pause
        result = await fsm.transition_to("paused")
        assert result.is_ok(), f"Transition to paused should succeed: {result}"
        assert await fsm.get_state() == "paused"

        # Resume
        result = await fsm.transition_to("running")
        assert result.is_ok(), f"Transition back to running should succeed: {result}"
        assert await fsm.get_state() == "running"

    @pytest.mark.asyncio
    async def test_lifecycle_fsm_cancellation(self):
        """Test lifecycle FSM cancellation: idle → cancelled."""
        config = _unwrap_agent_config(create_autonomous_worker_agent())
        fsm = config.lifecycle_fsm

        # Cancel from idle
        result = await fsm.transition_to("cancelled")
        assert result.is_ok(), f"Transition to cancelled should succeed: {result}"
        assert await fsm.get_state() == "cancelled"

    # ========================================================================
    # Workflow FSM Transition Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_workflow_fsm_linear_flow(self):
        """Test workflow FSM linear flow: intake → plan → act → synthesize → check."""
        config = _unwrap_agent_config(create_consultant_agent())
        fsm = config.workflow_fsm

        # Verify initial state
        state = await fsm.get_state()
        assert state == "intake", "Workflow FSM should start in intake state"

        # Navigate through linear flow
        transitions = [
            ("intake", "plan"),
            ("plan", "act"),
            ("act", "synthesize"),
            ("synthesize", "check"),
        ]

        for from_state, to_state in transitions:
            is_valid = await fsm.is_transition_valid(from_state, to_state)
            assert is_valid, f"Transition {from_state} → {to_state} should be valid"

            result = await fsm.transition_to(to_state)
            assert result.is_ok(), f"Transition to {to_state} should succeed: {result}"

            state = await fsm.get_state()
            assert state == to_state, f"FSM should be in {to_state} state"

    @pytest.mark.asyncio
    async def test_workflow_fsm_loop_transition(self):
        """Test workflow FSM loop: check → plan (continue iteration)."""
        config = _unwrap_agent_config(create_pre_planning_agent())
        fsm = config.workflow_fsm

        # Navigate to check state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")

        # Verify loop transition is valid
        is_valid = await fsm.is_transition_valid("check", "plan")
        assert is_valid, "Transition check → plan should be valid (loop)"

        # Execute loop transition
        result = await fsm.transition_to("plan")
        assert result.is_ok(), f"Loop transition should succeed: {result}"

        # Verify we're back at plan state
        state = await fsm.get_state()
        assert state == "plan", "FSM should be back at plan state for next iteration"

    @pytest.mark.asyncio
    async def test_workflow_fsm_exit_transition(self):
        """Test workflow FSM exit: check → done (exit workflow)."""
        config = _unwrap_agent_config(create_plan_validator_agent())
        fsm = config.workflow_fsm

        # Navigate to check state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")

        # Verify exit transition is valid
        is_valid = await fsm.is_transition_valid("check", "done")
        assert is_valid, "Transition check → done should be valid (exit)"

        # Execute exit transition
        result = await fsm.transition_to("done")
        assert result.is_ok(), f"Exit transition should succeed: {result}"

        # Verify we're at done state
        state = await fsm.get_state()
        assert state == "done", "FSM should be at done state (workflow complete)"

    @pytest.mark.asyncio
    async def test_workflow_fsm_multiple_iterations(self):
        """Test workflow FSM multiple loop iterations."""
        config = _unwrap_agent_config(create_librarian_agent())
        fsm = config.workflow_fsm

        # First iteration: intake → plan → act → synthesize → check
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")
        assert await fsm.get_state() == "check"

        # Loop back to plan (iteration 2)
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")
        assert await fsm.get_state() == "check"

        # Loop back to plan (iteration 3)
        await fsm.transition_to("plan")
        assert await fsm.get_state() == "plan"

    @pytest.mark.asyncio
    async def test_workflow_fsm_reset_after_done(self):
        """Test workflow FSM reset: done → intake."""
        config = _unwrap_agent_config(create_master_orchestrator_agent())
        fsm = config.workflow_fsm

        # Navigate to done state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")
        await fsm.transition_to("done")

        # Verify reset transition is valid
        is_valid = await fsm.is_transition_valid("done", "intake")
        assert is_valid, "Transition done → intake should be valid (reset)"

        # Execute reset transition
        result = await fsm.transition_to("intake")
        assert result.is_ok(), f"Reset transition should succeed: {result}"

        # Verify we're back at intake state
        state = await fsm.get_state()
        assert state == "intake", "FSM should be back at intake state for next task"

    # ========================================================================
    # Combined FSM State Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_fsm_state_on_agent_failure(self):
        """Test that FSM states are properly set on agent failure."""
        config = _unwrap_agent_config(create_multimodal_looker_agent())

        lifecycle_fsm = config.lifecycle_fsm
        workflow_fsm = config.workflow_fsm

        # Simulate agent lifecycle: start, run, fail
        await lifecycle_fsm.transition_to("running")
        assert await lifecycle_fsm.get_state() == "running"

        await workflow_fsm.transition_to("plan")
        await workflow_fsm.transition_to("act")

        # Simulate failure during execution
        await lifecycle_fsm.transition_to("failed")
        assert await lifecycle_fsm.get_state() == "failed", (
            "Lifecycle FSM should be in failed state"
        )

        # Workflow FSM remains in its last state (act)
        assert await workflow_fsm.get_state() == "act", "Workflow FSM should remain in act state"

    @pytest.mark.asyncio
    async def test_fsm_state_on_agent_cancellation(self):
        """Test that FSM states are properly set on agent cancellation."""
        config = _unwrap_agent_config(create_frontend_ui_ux_skill())

        lifecycle_fsm = config.lifecycle_fsm
        workflow_fsm = config.workflow_fsm

        # Start execution
        await lifecycle_fsm.transition_to("running")
        await workflow_fsm.transition_to("plan")

        # Simulate cancellation
        await lifecycle_fsm.transition_to("cancelled")
        assert await lifecycle_fsm.get_state() == "cancelled", (
            "Lifecycle FSM should be in cancelled state"
        )

        # Workflow FSM remains in its last state (plan)
        assert await workflow_fsm.get_state() == "plan", "Workflow FSM should remain in plan state"

    @pytest.mark.asyncio
    async def test_fsm_state_on_successful_completion(self):
        """Test that both FSMs reach completion on successful agent run."""
        config = _unwrap_agent_config(create_orchestrator_agent())

        lifecycle_fsm = config.lifecycle_fsm
        workflow_fsm = config.workflow_fsm

        # Simulate full successful lifecycle
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("completed")
        assert await lifecycle_fsm.get_state() == "completed", (
            "Lifecycle FSM should be in completed state"
        )

        # Simulate full successful workflow
        await workflow_fsm.transition_to("plan")
        await workflow_fsm.transition_to("act")
        await workflow_fsm.transition_to("synthesize")
        await workflow_fsm.transition_to("check")
        await workflow_fsm.transition_to("done")
        assert await workflow_fsm.get_state() == "done", "Workflow FSM should be in done state"

    @pytest.mark.asyncio
    async def test_all_agents_have_valid_lifecycle_fsm_states(self):
        """Test that all agents have lifecycle FSM with valid initial state."""
        agents = [
            _unwrap_agent_config(create_orchestrator_agent()),
            _unwrap_agent_config(create_master_orchestrator_agent()),
            _unwrap_agent_config(create_planner_agent()),
            _unwrap_agent_config(create_autonomous_worker_agent()),
            _unwrap_agent_config(create_consultant_agent()),
            _unwrap_agent_config(create_pre_planning_agent()),
            _unwrap_agent_config(create_plan_validator_agent()),
            _unwrap_agent_config(create_librarian_agent()),
            _unwrap_agent_config(create_explore_agent()),
            _unwrap_agent_config(create_frontend_ui_ux_skill()),
            _unwrap_agent_config(create_multimodal_looker_agent()),
        ]

        for config in agents:
            state = await config.lifecycle_fsm.get_state()
            assert state == "idle", (
                f"Agent {config.agent.name} lifecycle FSM should start in idle state, got {state}"
            )

    @pytest.mark.asyncio
    async def test_all_agents_have_valid_workflow_fsm_states(self):
        """Test that all agents have workflow FSM with valid initial state."""
        agents = [
            _unwrap_agent_config(create_orchestrator_agent()),
            _unwrap_agent_config(create_master_orchestrator_agent()),
            _unwrap_agent_config(create_planner_agent()),
            _unwrap_agent_config(create_autonomous_worker_agent()),
            _unwrap_agent_config(create_consultant_agent()),
            _unwrap_agent_config(create_pre_planning_agent()),
            _unwrap_agent_config(create_plan_validator_agent()),
            _unwrap_agent_config(create_librarian_agent()),
            _unwrap_agent_config(create_explore_agent()),
            _unwrap_agent_config(create_frontend_ui_ux_skill()),
            _unwrap_agent_config(create_multimodal_looker_agent()),
        ]

        for config in agents:
            state = await config.workflow_fsm.get_state()
            assert state == "intake", (
                f"Agent {config.agent.name} workflow FSM should start in intake state, got {state}"
            )
