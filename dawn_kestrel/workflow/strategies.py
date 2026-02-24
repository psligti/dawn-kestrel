"""Reasoning strategy protocol for decision-making in workflow states.

This module defines the ReasoningStrategy protocol that specifies the interface
for reasoning strategies (CoT, ReAct, etc.) used by the REASON state to decide
the next action.

Key concepts:
- ReasoningContext: Input context for reasoning decisions
- ReasoningResult: Output containing thought, action, and next state
- ReasoningStrategy: Protocol for strategy implementations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ReasoningContext:
    """Input context for reasoning strategy decisions.

    Provides all information needed for a reasoning strategy to make
    a decision about the next action in the workflow.

    Attributes:
        current_state: The current FSM state name.
        available_actions: List of actions that can be taken.
        evidence: Evidence references from previous steps.
        constraints: Budget/iteration constraints.
    """

    current_state: str
    available_actions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    """Output from a reasoning strategy decision.

    Contains the thought process, selected action, and target state
    for the FSM transition.

    Attributes:
        thought: The reasoning behind the decision.
        action: The action to take.
        next_state: The target FSM state after this action.
    """

    thought: str
    action: str
    next_state: str


@runtime_checkable
class ReasoningStrategy(Protocol):
    """Protocol for reasoning strategy implementations.

    A reasoning strategy analyzes the current context and decides
    what action to take next. Different strategies (CoT, ReAct, etc.)
    implement different reasoning approaches.

    Example:
        class ChainOfThoughtStrategy:
            def decide(self, context: ReasoningContext) -> ReasoningResult:
                # Analyze context and generate thought chain
                return ReasoningResult(
                    thought="Analyzing evidence...",
                    action="analyze",
                    next_state="ACT"
                )
    """

    def decide(self, context: ReasoningContext) -> ReasoningResult:
        """Make a decision based on the reasoning context.

        Args:
            context: The current reasoning context with state, evidence,
                and constraints.

        Returns:
            ReasoningResult: The decision with thought, action, and next state.
        """
        ...


class CoTStrategy:
    """Chain-of-Thought reasoning strategy.

    Implements linear chain-of-thought reasoning: analyze → plan → execute.
    This strategy analyzes available evidence and selects the most appropriate
    next action based on the current context.

    Example:
        strategy = CoTStrategy()
        context = ReasoningContext(
            current_state="REASON",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["file.py:10-20"],
        )
        result = strategy.decide(context)
        # result.thought contains the reasoning chain
        # result.action contains the selected action
    """

    def decide(self, context: ReasoningContext) -> ReasoningResult:
        """Make a decision using chain-of-thought reasoning."""
        evidence_count = len(context.evidence)

        if evidence_count == 0:
            return ReasoningResult(
                thought="No evidence available. Beginning analysis phase.",
                action="analyze",
                next_state="ACT",
            )

        if "complete" in context.available_actions and evidence_count >= 2:
            return ReasoningResult(
                thought=f"Sufficient evidence collected ({evidence_count} items). Proceeding to complete.",
                action="complete",
                next_state="DONE",
            )

        return ReasoningResult(
            thought=f"Evidence gathered ({evidence_count} items). Continuing analysis.",
            action=context.available_actions[0] if context.available_actions else "analyze",
            next_state="ACT",
        )


class ReActStrategy:
    """ReAct (Reason-Act-Observe) reasoning strategy implementation.

    Implements the ReAct pattern where reasoning proceeds in cycles:
    1. Reason: Analyze the current state and any observations
    2. Act: Decide on an action to take
    3. Observe: Review results (handled externally, passed as evidence)

    The strategy examines previous observations from the context and
    decides what action to take next based on the ReAct pattern.

    Example:
        strategy = ReActStrategy()
        context = ReasoningContext(
            current_state="REASON",
            evidence=["observation:grep_found_3_files"],
            available_actions=["analyze", "delegate", "complete"],
        )
        result = strategy.decide(context)
        # result.thought contains reasoning about observation
        # result.action contains next action to take
    """

    def decide(self, context: ReasoningContext) -> ReasoningResult:
        """Make a decision using the ReAct pattern.

        Examines any observations from previous steps in the evidence,
        reasons about them, and decides the next action.

        Args:
            context: The reasoning context containing current state,
                available actions, evidence (including observations),
                and constraints.

        Returns:
            ReasoningResult with thought (reasoning trace), action
            (next step), and next_state (target FSM state).
        """
        # Check for observation from previous step
        observation = self._extract_observation(context.evidence)

        if observation:
            # We have an observation - reason about it and decide next action
            thought = f"Observation received: {observation}. Analyzing implications."
            action = self._select_action_from_observation(observation, context.available_actions)
        else:
            # No observation yet - initial reasoning step
            thought = "Starting reasoning process. No prior observations to analyze."
            action = self._select_initial_action(context.available_actions)

        next_state = self._determine_next_state(action, context.available_actions)

        return ReasoningResult(
            thought=thought,
            action=action,
            next_state=next_state,
        )

    def _extract_observation(self, evidence: list[str]) -> str | None:
        """Extract the most recent observation from evidence.

        Observations are identified by the 'observation:' prefix
        in the evidence list.

        Args:
            evidence: List of evidence strings from context.

        Returns:
            The observation content without prefix, or None if no observation.
        """
        for item in reversed(evidence):  # Most recent first
            if item.startswith("observation:"):
                return item[len("observation") + 1 :]
        return None

    def _select_action_from_observation(
        self, observation: str, available_actions: list[str]
    ) -> str:
        """Select next action based on observation analysis.

        Args:
            observation: The observation content from previous step.
            available_actions: Actions that can be taken.

        Returns:
            Selected action string.
        """
        # Simple heuristic: prefer 'analyze' if available after observation
        if "analyze" in available_actions:
            return "analyze"
        if available_actions:
            return available_actions[0]
        return "act"

    def _select_initial_action(self, available_actions: list[str]) -> str:
        """Select initial action when no observation exists.

        Args:
            available_actions: Actions that can be taken.

        Returns:
            Selected action string.
        """
        if available_actions:
            return available_actions[0]
        return "act"

    def _determine_next_state(self, action: str, available_actions: list[str]) -> str:
        """Determine the target FSM state based on action.

        Args:
            action: The selected action.
            available_actions: Actions that can be taken.

        Returns:
            Target state name for FSM transition.
        """
        # Map actions to states
        action_to_state = {
            "complete": "DONE",
            "synthesize": "SYNTHESIZE",
            "check": "CHECK",
            "delegate": "ACT",
        }

        # Check if action maps to a specific state
        if action in action_to_state:
            return action_to_state[action]

        # Default to ACT state for most actions
        return "ACT"
