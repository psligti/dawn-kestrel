"""Evaluation hooks for ash-hawk integration.

This module provides the hooks that dawn-kestrel exposes for evaluation
frameworks like ash-hawk. The hooks allow external systems to:
- Monitor transcript generation
- Track tool calls
- Record phase completions
- Monitor budget consumption

The grading framework and judge normalization stay in ash-hawk.
Dawn-kestrel provides the data via these hooks.

Usage:
    from dawn_kestrel.evaluation.hooks import EvaluationHooks

    hooks = EvaluationHooks()
    hooks.on_transcript_ready = lambda t: evaluator.record(t)
    hooks.on_tool_call = lambda t, i, o: evaluator.track_tool(t, i, o)

    session = Session(hooks=hooks)
    await session.run(prompt)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dawn_kestrel.evaluation.models import Transcript


@runtime_checkable
class TranscriptCallback(Protocol):
    """Protocol for transcript callback."""

    def __call__(self, transcript: Transcript) -> None: ...


@runtime_checkable
class ToolCallCallback(Protocol):
    """Protocol for tool call callback."""

    def __call__(self, tool: str, input: dict[str, Any], output: Any) -> None: ...


@runtime_checkable
class PhaseCallback(Protocol):
    """Protocol for phase completion callback."""

    def __call__(self, phase: str, output: dict[str, Any]) -> None: ...


@runtime_checkable
class BudgetCallback(Protocol):
    """Protocol for budget threshold callback."""

    def __call__(self, usage: dict[str, Any], threshold: float) -> None: ...


class EvaluationHooks:
    """Hooks that ash-hawk can attach to for evaluation.

    This provides a clean interface between dawn-kestrel SDK and
    ash-hawk evaluation framework. Ash-hawk attaches callbacks to
    capture data needed for grading.

    Attributes:
        on_transcript_ready: Called when a transcript is complete
        on_tool_call: Called for each tool invocation
        on_phase_complete: Called when an FSM phase completes
        on_budget_threshold: Called when budget threshold is reached

    Example:
        hooks = EvaluationHooks()
        hooks.on_transcript_ready = lambda t: print(f"Transcript: {t.id}")

        session = Session(hooks=hooks)
    """

    on_transcript_ready: TranscriptCallback | None = None
    on_tool_call: ToolCallCallback | None = None
    on_phase_complete: PhaseCallback | None = None
    on_budget_threshold: BudgetCallback | None = None

    def emit_transcript(self, transcript: Transcript) -> None:
        """Emit a transcript to the callback if set."""
        if self.on_transcript_ready is not None:
            self.on_transcript_ready(transcript)

    def emit_tool_call(
        self,
        tool: str,
        input: dict[str, Any],
        output: Any,
    ) -> None:
        """Emit a tool call event to the callback if set."""
        if self.on_tool_call is not None:
            self.on_tool_call(tool, input, output)

    def emit_phase(self, phase: str, output: dict[str, Any]) -> None:
        """Emit a phase completion event to the callback if set."""
        if self.on_phase_complete is not None:
            self.on_phase_complete(phase, output)

    def emit_budget(self, usage: dict[str, Any], threshold: float) -> None:
        """Emit a budget threshold event to the callback if set."""
        if self.on_budget_threshold is not None:
            self.on_budget_threshold(usage, threshold)

    def has_hooks(self) -> bool:
        """Check if any hooks are configured."""
        return any(
            [
                self.on_transcript_ready is not None,
                self.on_tool_call is not None,
                self.on_phase_complete is not None,
                self.on_budget_threshold is not None,
            ]
        )


class HookManager:
    """Manages evaluation hooks across a session.

    Provides a central point for emitting events to multiple
    registered hooks.

    Example:
        manager = HookManager()
        manager.register(hook1)
        manager.register(hook2)

        manager.emit_transcript(transcript)
    """

    def __init__(self) -> None:
        self._hooks: list[EvaluationHooks] = []

    def register(self, hooks: EvaluationHooks) -> None:
        """Register a hooks instance."""
        self._hooks.append(hooks)

    def unregister(self, hooks: EvaluationHooks) -> None:
        """Unregister a hooks instance."""
        if hooks in self._hooks:
            self._hooks.remove(hooks)

    def emit_transcript(self, transcript: Transcript) -> None:
        """Emit transcript to all registered hooks."""
        for hooks in self._hooks:
            hooks.emit_transcript(transcript)

    def emit_tool_call(
        self,
        tool: str,
        input: dict[str, Any],
        output: Any,
    ) -> None:
        """Emit tool call to all registered hooks."""
        for hooks in self._hooks:
            hooks.emit_tool_call(tool, input, output)

    def emit_phase(self, phase: str, output: dict[str, Any]) -> None:
        """Emit phase completion to all registered hooks."""
        for hooks in self._hooks:
            hooks.emit_phase(phase, output)

    def emit_budget(self, usage: dict[str, Any], threshold: float) -> None:
        """Emit budget threshold to all registered hooks."""
        for hooks in self._hooks:
            hooks.emit_budget(usage, threshold)


__all__ = [
    "TranscriptCallback",
    "ToolCallCallback",
    "PhaseCallback",
    "BudgetCallback",
    "EvaluationHooks",
    "HookManager",
]
