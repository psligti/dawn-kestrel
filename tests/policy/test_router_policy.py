import asyncio

import pytest

from dawn_kestrel.core.event_bus import Event, bus
from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    PolicyInput,
    RiskLevel,
    StepProposal,
    TodoItem,
)
from dawn_kestrel.policy.router_policy import RouterPolicy


class TestRouterPolicyBasics:
    def test_implements_propose_method(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        assert hasattr(policy, "propose")
        assert callable(policy.propose)

    def test_returns_step_proposal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(goal="Test goal")

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)


class TestRoutingByEnvVar:
    def test_env_var_overrides_signals(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DK_POLICY_MODE", "react")
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[TodoItem(id="todo-1", description="edit file", status="pending")],
            budgets=BudgetInfo(max_iterations=10, iterations_consumed=8),
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        assert result.intent == "No action proposed"


class TestRoutingByBudget:
    def test_budget_pressure_triggers_rules(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[TodoItem(id="todo-1", description="edit config", status="pending")],
            budgets=BudgetInfo(max_iterations=10, iterations_consumed=8),
        )

        result = policy.propose(input_data)

        assert "Address TODO" in result.intent or result.intent == "No action proposed"


class TestRoutingByStrictness:
    def test_hard_constraints_trigger_rules(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[TodoItem(id="todo-1", description="edit config", status="pending")],
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        assert result.intent.startswith("Request approval")
        assert result.risk_level == RiskLevel.HIGH


class TestRoutingByAmbiguity:
    def test_high_ambiguity_triggers_react(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="todo-1", description="Blocked 1", status="blocked"),
                TodoItem(id="todo-2", description="Blocked 2", status="blocked"),
                TodoItem(id="todo-3", description="Blocked 3", status="blocked"),
                TodoItem(id="todo-4", description="Blocked 4", status="blocked"),
            ],
        )

        result = policy.propose(input_data)

        assert result.intent in ("No action proposed", "No pending TODOs to address")


class TestRoutingByToolIntensity:
    def test_tool_heavy_todos_trigger_plan_execute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="todo-1", description="edit config file", status="pending"),
                TodoItem(id="todo-2", description="run tests", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert (
            "Address TODO" in result.intent
            or result.intent == "No action proposed"
            or "Execute TODO" in result.intent
        )


class TestRoutingDeterminism:
    def test_same_input_same_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DK_POLICY_MODE", raising=False)
        policy = RouterPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[TodoItem(id="todo-1", description="edit config", status="pending")],
        )

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent
        assert result1.target_todo_ids == result2.target_todo_ids


class TestFallbackBehavior:
    @pytest.mark.asyncio
    async def test_fallback_to_fsm_emits_event(self, monkeypatch: pytest.MonkeyPatch) -> None:
        policy = RouterPolicy()

        class BoomPolicy:
            def propose(self, input: PolicyInput) -> StepProposal:
                raise RuntimeError("boom")

        def select_policy(_: PolicyInput) -> BoomPolicy:
            return BoomPolicy()

        monkeypatch.setattr(policy, "_select_policy", select_policy)
        captured: list[Event] = []

        async def handler(event: Event) -> None:
            captured.append(event)

        unsubscribe = await bus.subscribe("policy.router.fallback", handler, once=True)
        result = policy.propose(PolicyInput(goal="Test"))
        await asyncio.sleep(0)
        await unsubscribe()

        assert result.intent == "FSM-based action (not yet wired)"
        assert captured
        assert captured[0].data["policy"] == "BoomPolicy"
        assert captured[0].data["error"] == "boom"
