"""Policy engine for agent decision-making.

This package provides the pluggable policy engine that governs agent
behavior at runtime. The policy engine:

1. Evaluates proposed actions against constraints and budgets
2. Validates completion claims against available evidence
3. Enforces behavioral boundaries and tool surface policies
4. Provides structured decision-making for action approval/rejection

The core contracts module defines all typed data models for
communication between agents and policy evaluators.
"""

from dawn_kestrel.policy.actions import (
    ActionDispatcher,
    ActionHandler,
    ActionResult,
    ReadFileHandler,
    UnknownActionTypeError,
)
from dawn_kestrel.policy.contracts import (
    Action,
    BudgetInfo,
    Constraint,
    ContextRequest,
    EditFileAction,
    EventSummary,
    PolicyInput,
    ReadFileAction,
    RequestApprovalAction,
    RiskLevel,
    RunTestsAction,
    SearchRepoAction,
    StepProposal,
    SummarizeAction,
    TodoCompletionClaim,
    TodoItem,
    UpsertTodosAction,
)
from dawn_kestrel.policy.engine import (
    DefaultPolicyEngine,
    PolicyEngine,
    ProposalRejected,
)
from dawn_kestrel.policy.fsm_bridge import FSMPolicy
from dawn_kestrel.policy.invariants import (
    HarnessGate,
    HarnessInvariants,
)
from dawn_kestrel.policy.plan_execute_policy import PlanExecutePolicy
from dawn_kestrel.policy.react_policy import ReActPolicy
from dawn_kestrel.policy.rules_policy import RulesPolicy
from dawn_kestrel.policy.validator import (
    VALID_ACTION_TYPES,
    ProposalValidator,
    ValidationResult,
)

__all__ = [
    "RiskLevel",
    "Action",
    "ReadFileAction",
    "SearchRepoAction",
    "EditFileAction",
    "RunTestsAction",
    "UpsertTodosAction",
    "RequestApprovalAction",
    "SummarizeAction",
    "ContextRequest",
    "TodoCompletionClaim",
    "TodoItem",
    "EventSummary",
    "BudgetInfo",
    "Constraint",
    "PolicyInput",
    "StepProposal",
    "PolicyEngine",
    "DefaultPolicyEngine",
    "RulesPolicy",
    "PlanExecutePolicy",
    "ProposalRejected",
    "ActionHandler",
    "ActionResult",
    "ActionDispatcher",
    "ReadFileHandler",
    "UnknownActionTypeError",
    "ProposalValidator",
    "ValidationResult",
    "VALID_ACTION_TYPES",
    "FSMPolicy",
    "ReActPolicy",
    "HarnessInvariants",
    "HarnessGate",
]
from dawn_kestrel.policy.delegation import (
    DelegationDecision,
    DelegationContext,
    DelegationOutput,
    DelegationPolicy,
    SubtaskProposal,
    CompositeDelegationPolicy,
    DefaultDelegationPolicy,
)
from dawn_kestrel.policy.builtin import (
    ComplexityBasedDelegationPolicy,
    BudgetAwareDelegationPolicy,
    StagnationAwarePolicy,
    DomainBasedDelegationPolicy,
)

