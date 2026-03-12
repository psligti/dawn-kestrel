"""Evaluation module for Dawn Kestrel.

This module provides data models for agent evaluation, enabling
external evaluation harnesses (like ash-hawk) to run evaluations
against dawn-kestrel agents.
"""

from dawn_kestrel.evaluation.models import (
    Task,
    Trial,
    Transcript,
    Outcome,
    Suite,
    SuiteRun,
)
from dawn_kestrel.evaluation.grader_specs import (
    GraderSpec,
    GRADER_TYPE_DETERMINISTIC_TESTS,
    GRADER_TYPE_LLM_RUBRIC,
    GRADER_TYPE_STATIC_ANALYSIS,
    GRADER_TYPE_STATE_CHECK,
    GRADER_TYPE_TOOL_CALLS,
    GRADER_TYPE_TRANSCRIPT,
)

from dawn_kestrel.evaluation.hooks import (
    BudgetCallback,
    EvaluationHooks,
    HookManager,
    PhaseCallback,
    ToolCallCallback,
    TranscriptCallback,
)

from dawn_kestrel.evaluation.runner import (
    AgentRunner,
    AgentRunnerProtocol,
    RunnerConfig,
    RunnerResult,
)

__all__ = [
    "Task",
    "Trial",
    "Transcript",
    "Outcome",
    "Suite",
    "SuiteRun",
    "GraderSpec",
    "GRADER_TYPE_DETERMINISTIC_TESTS",
    "GRADER_TYPE_LLM_RUBRIC",
    "GRADER_TYPE_STATIC_ANALYSIS",
    "GRADER_TYPE_STATE_CHECK",
    "GRADER_TYPE_TOOL_CALLS",
    "GRADER_TYPE_TRANSCRIPT",
    # Hooks for ash-hawk integration
    "BudgetCallback",
    "EvaluationHooks",
    "HookManager",
    "PhaseCallback",
    "ToolCallCallback",
    "TranscriptCallback",
    # Runner for ash-hawk integration
    "AgentRunner",
    "AgentRunnerProtocol",
    "RunnerConfig",
    "RunnerResult",
]

