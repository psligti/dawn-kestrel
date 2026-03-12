# Dawn Kestrel Safety Hardening Specification

**Version:** 2.0.0  
**Status:** Draft  
**Target Release:** dawn-kestrel v2.0.0  
**Architecture:** Policy-Based (FSM removed)  
**Author:** Based on bolt-merlin agent readiness evaluation

---

## Executive Summary

This specification defines changes to make dawn-kestrel's safety mechanisms **opt-out** rather than **opt-in**, using the policy engine as the sole decision-making layer. All safety enforcement flows through `PolicyEngine` → `HarnessGate` → `HarnessInvariants`.

### Architecture Principle

```
Agent Action Request
        │
        ▼
┌──────────────────┐
│  PolicyEngine    │  ← Decision layer
│  (RouterPolicy)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   HarnessGate    │  ← Enforcement layer
│   .enforce()     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ HarnessInvariants│  ← Safety rules
│  - Risk classify │
│  - Verify claims │
│  - Check budget  │
└────────┬─────────┘
         │
         ▼
   Approved / Rejected
```

### Goals

1. **Mandatory verification** before task completion claims
2. **Risk-aware operation handling** with automatic approval gates
3. **Explicit success criteria** in task definitions
4. **Token/cost tracking** via `BudgetInfo` with configurable thresholds
5. **Programmatic 3-strike failure rule** enforcement at runtime level
6. **Irreversible operation protection**

### Non-Goals

- FSM-based state management (deprecated)
- Changes to agent prompts (application-level concern)
- New UI/UX for approvals (handled by consuming applications)
- Distributed/multi-process safety (single-process scope)

---

## Specification

### 1. Policy Engine Enablement

**Problem:** Safety mechanisms exist but require `DK_POLICY_ENGINE=1` environment variable.

**Solution:** Enable by default, allow opt-out.

#### 1.1 Default Enablement

**File:** `dawn_kestrel/agents/runtime.py`

```python
# Current (line 110):
self._policy_enabled = os.getenv("DK_POLICY_ENGINE", "0") == "1"

# Change to:
self._policy_enabled = os.getenv("DK_POLICY_ENGINE", "1") != "0"
```

**Rationale:** Safety should be the default. `DK_POLICY_ENGINE=0` explicitly disables.

#### 1.2 Configuration via Settings

**File:** `dawn_kestrel/core/settings.py`

Add new settings class:

```python
from pydantic import Field
from typing import Literal

class SafetySettings:
    """Safety and policy configuration."""
    
    # Policy Engine
    policy_engine_enabled: bool = Field(default=True)
    policy_mode: Literal["rules", "react", "plan_execute", "strict"] = Field(default="strict")
    
    # Budget Defaults (used to populate BudgetInfo)
    default_max_cost_usd: float = Field(default=10.0, ge=0.0)
    default_max_iterations: int = Field(default=100, ge=1)
    default_max_tool_calls: int = Field(default=1000, ge=1)
    default_max_wall_time_seconds: float = Field(default=3600.0, ge=1.0)
    default_max_subagent_calls: int = Field(default=50, ge=0)
    default_max_tokens_input: int = Field(default=1_000_000, ge=0)
    default_max_tokens_output: int = Field(default=100_000, ge=0)
    
    # Failure Handling
    max_consecutive_failures: int = Field(default=3, ge=1, le=10)
    failure_rollback_enabled: bool = Field(default=True)
    
    # Verification Requirements
    require_verification_for_edits: bool = Field(default=True)
    require_verification_for_tests: bool = Field(default=True)
    
    # Approval Requirements
    auto_approve_low_risk: bool = Field(default=True)
    require_approval_for_high_risk: bool = Field(default=True)
    require_approval_for_irreversible: bool = Field(default=True)
    
    # Audit
    safety_audit_enabled: bool = Field(default=True)
    audit_log_path: str | None = Field(default=None)


class Settings:
    """Application settings."""
    
    # ... existing settings ...
    
    safety: SafetySettings = Field(default_factory=SafetySettings)
```

#### 1.3 Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `DK_POLICY_ENGINE` | `0`, `1` | `1` | Master toggle for policy enforcement |
| `DK_POLICY_MODE` | `rules`, `react`, `plan_execute`, `strict` | `strict` | Policy implementation to use |
| `DK_SAFETY_AUDIT` | `0`, `1` | `1` | Log all safety decisions |
| `DK_MAX_COST_USD` | `float` | `10.0` | Default cost limit |
| `DK_MAX_CONSECUTIVE_FAILURES` | `int` | `3` | Strike limit |

---

### 2. Risk Classification System

**Problem:** Risk levels exist but aren't enforced for all dangerous operations.

**Solution:** Comprehensive risk classification with automatic gates.

#### 2.1 Extended Risk Levels

**File:** `dawn_kestrel/policy/contracts.py`

```python
class RiskLevel(str, Enum):
    """Risk level for step proposals with specific enforcement requirements.
    
    Values:
        LOW: Read-only, no side effects - auto-approve
        MED: Modifies files, runs tests - may require verification
        HIGH: Git operations, deletions - requires approval
        CRITICAL: Irreversible, production-affecting - requires approval + confirmation
    """
    
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

#### 2.2 Action Risk Classification

**File:** `dawn_kestrel/policy/risk_classification.py` (new file)

```python
"""Action-to-risk classification mapping for safety enforcement.

This module provides the central risk classification system used by
HarnessInvariants to determine approval and verification requirements.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dawn_kestrel.policy.contracts import RiskLevel


class ActionRiskClassification:
    """Maps action types to risk levels and enforcement requirements.
    
    Risk levels determine the enforcement behavior:
    
    | Risk Level | Approval | Verification | Examples |
    |------------|----------|--------------|----------|
    | LOW        | No       | No           | read, list, search |
    | MED        | No       | Optional     | run_tests, build |
    | HIGH       | Yes      | Yes          | edit_file, git_commit |
    | CRITICAL   | Yes      | Yes + Confirm| git_push, delete |
    
    Classification rules:
    1. IRREVERSIBLE actions are always CRITICAL
    2. HIGH_RISK actions default to HIGH
    3. MEDIUM_RISK actions default to MED
    4. Everything else is LOW
    """
    
    # Irreversible actions - always CRITICAL, require double-confirm
    IRREVERSIBLE_ACTIONS = frozenset({
        "DELETE_FILE",
        "GIT_PUSH",
        "GIT_FORCE_PUSH",
        "GIT_RESET_HARD",
        "GIT_REBASE",
        "DROP_TABLE",
        "TRUNCATE_TABLE",
        "DROP_DATABASE",
        "DELETE_BRANCH",
        "REMOVE_REMOTE",
        "FORCE_MERGE",
    })
    
    # High-risk actions - require approval before execution
    HIGH_RISK_ACTIONS = frozenset({
        "EDIT_FILE",
        "WRITE_FILE",
        "GIT_COMMIT",
        "GIT_MERGE",
        "GIT_CHECKOUT",
        "RUN_MIGRATION",
        "MODIFY_CONFIG",
        "CHANGE_PERMISSIONS",
        "INSTALL_PACKAGE",
        "UNINSTALL_PACKAGE",
        "EXECUTE_SHELL",
    })
    
    # Medium-risk actions - may require verification after execution
    MEDIUM_RISK_ACTIONS = frozenset({
        "RUN_TESTS",
        "RUN_BUILD",
        "RUN_LINT",
        "TYPE_CHECK",
        "EXECUTE_COMMAND",
        "APPLY_PATCH",
    })
    
    # Low-risk actions - no approval or verification required
    LOW_RISK_ACTIONS = frozenset({
        "READ_FILE",
        "LIST_DIRECTORY",
        "GET_SYMBOL",
        "FIND_REFERENCES",
        "SEARCH_REPO",
        "SUMMARIZE",
        "CONTEXT_REQUEST",
        "UPSERT_TODOS",
    })
    
    @classmethod
    def classify(cls, action_type: str) -> "RiskLevel":
        """Classify an action type into a risk level.
        
        Args:
            action_type: The action type string (e.g., "EDIT_FILE")
            
        Returns:
            RiskLevel enum value
            
        Example:
            >>> ActionRiskClassification.classify("GIT_PUSH")
            <RiskLevel.CRITICAL: 'CRITICAL'>
            >>> ActionRiskClassification.classify("READ_FILE")
            <RiskLevel.LOW: 'LOW'>
        """
        from dawn_kestrel.policy.contracts import RiskLevel
        
        if action_type in cls.IRREVERSIBLE_ACTIONS:
            return RiskLevel.CRITICAL
        if action_type in cls.HIGH_RISK_ACTIONS:
            return RiskLevel.HIGH
        if action_type in cls.MEDIUM_RISK_ACTIONS:
            return RiskLevel.MED
        return RiskLevel.LOW
    
    @classmethod
    def requires_approval(cls, action_type: str) -> bool:
        """Check if action requires explicit approval before execution.
        
        HIGH and CRITICAL actions require approval.
        
        Args:
            action_type: The action type to check
            
        Returns:
            True if approval is required
        """
        return action_type in cls.HIGH_RISK_ACTIONS or action_type in cls.IRREVERSIBLE_ACTIONS
    
    @classmethod
    def requires_verification(cls, action_type: str) -> bool:
        """Check if action requires verification after execution.
        
        MED, HIGH, and CRITICAL actions require verification.
        
        Args:
            action_type: The action type to check
            
        Returns:
            True if verification is required
        """
        return (
            action_type in cls.MEDIUM_RISK_ACTIONS or
            action_type in cls.HIGH_RISK_ACTIONS or
            action_type in cls.IRREVERSIBLE_ACTIONS
        )
    
    @classmethod
    def is_irreversible(cls, action_type: str) -> bool:
        """Check if action is irreversible (cannot be undone).
        
        Irreversible actions require special handling:
        - Double confirmation
        - Detailed audit logging
        - No automatic retry
        
        Args:
            action_type: The action type to check
            
        Returns:
            True if action is irreversible
        """
        return action_type in cls.IRREVERSIBLE_ACTIONS
    
    @classmethod
    def get_all_action_types(cls) -> frozenset[str]:
        """Get all known action types across all risk levels.
        
        Returns:
            Frozen set of all classified action types
        """
        return (
            cls.IRREVERSIBLE_ACTIONS |
            cls.HIGH_RISK_ACTIONS |
            cls.MEDIUM_RISK_ACTIONS |
            cls.LOW_RISK_ACTIONS
        )


__all__ = ["ActionRiskClassification"]
```

#### 2.3 Update HarnessInvariants

**File:** `dawn_kestrel/policy/invariants.py`

```python
"""Safety invariants enforced by HarnessGate.

This module provides the safety enforcement layer that validates
all step proposals before execution. The invariants check:
1. Budget exhaustion
2. Approval requirements
3. Verification evidence
4. Irreversible action warnings
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dawn_kestrel.policy.risk_classification import ActionRiskClassification
from dawn_kestrel.policy.validator import ValidationResult

if TYPE_CHECKING:
    from dawn_kestrel.policy.contracts import StepProposal


class HarnessInvariants:
    """Safety invariants enforced by HarnessGate.
    
    These invariants represent hard safety rules that cannot be bypassed.
    They are checked in order of priority:
    
    1. BUDGET_EXHAUSTED - Stop immediately, no more actions allowed
    2. APPROVAL_REQUIRED - High-risk actions need explicit approval
    3. UNVERIFIED_COMPLETION - Completion claims need evidence
    4. IRREVERSIBLE_ACTION - Warning for irreversible operations
    
    Evidence Types Accepted:
        - test_passed: Tests executed successfully
        - build_succeeded: Build completed without errors
        - manual_review: Human reviewed and approved
        - lsp_diagnostics_clean: No LSP errors/warnings
        - type_check_passed: Type checking passed
    """
    
    _VERIFICATION_EVIDENCE_TYPES = frozenset({
        "test_passed",
        "build_succeeded",
        "manual_review",
        "lsp_diagnostics_clean",
        "type_check_passed",
    })
    
    _BUDGET_EXHAUSTED_MARKERS = frozenset({
        "budget_exhausted",
        "budget exhausted",
        "budget_exceeded",
        "budget exceeded",
        "token_limit_reached",
        "cost_limit_reached",
        "iteration_limit_reached",
    })
    
    def verify_before_done(self, proposal: "StepProposal") -> bool:
        """Check if completion claims have valid verification evidence.
        
        Args:
            proposal: The step proposal to validate
            
        Returns:
            True if no claims, or all claims have valid evidence
        """
        if not proposal.completion_claims:
            return True
        
        return any(
            claim.evidence_type in self._VERIFICATION_EVIDENCE_TYPES
            for claim in proposal.completion_claims
        )
    
    def approval_required(self, proposal: "StepProposal") -> bool:
        """Check if proposal satisfies approval requirements.
        
        For each action requiring approval, there must be a corresponding
        REQUEST_APPROVAL action in the proposal.
        
        Args:
            proposal: The step proposal to validate
            
        Returns:
            True if all approval requirements are satisfied
        """
        action_types = set(proposal.get_action_types())
        
        for action_type in action_types:
            if ActionRiskClassification.requires_approval(action_type):
                # Check if REQUEST_APPROVAL is present for this action
                if "REQUEST_APPROVAL" not in action_types:
                    return False  # Missing required approval
        
        return True  # Either no risky actions, or approval present
    
    def irreversible_action_present(self, proposal: "StepProposal") -> bool:
        """Check if proposal contains irreversible actions.
        
        Args:
            proposal: The step proposal to check
            
        Returns:
            True if any irreversible action is present
        """
        return any(
            ActionRiskClassification.is_irreversible(action_type)
            for action_type in proposal.get_action_types()
        )
    
    def budget_exhausted(self, proposal: "StepProposal") -> bool:
        """Check if budget is exhausted based on proposal notes.
        
        Args:
            proposal: The step proposal to check
            
        Returns:
            True if budget exhaustion is indicated
        """
        notes = getattr(proposal, 'notes', '') or ''
        notes_lower = notes.lower().strip()
        
        if not notes_lower:
            return False
        
        return any(marker in notes_lower for marker in self._BUDGET_EXHAUSTED_MARKERS)
    
    def get_missing_approvals(self, proposal: "StepProposal") -> list[str]:
        """Get list of action types missing required approval.
        
        Args:
            proposal: The step proposal to check
            
        Returns:
            List of action types that need approval but don't have it
        """
        action_types = set(proposal.get_action_types())
        missing = []
        
        for action_type in action_types:
            if ActionRiskClassification.requires_approval(action_type):
                if "REQUEST_APPROVAL" not in action_types:
                    missing.append(action_type)
        
        return missing
    
    def get_irreversible_actions(self, proposal: "StepProposal") -> list[str]:
        """Get list of irreversible actions in proposal.
        
        Args:
            proposal: The step proposal to check
            
        Returns:
            List of irreversible action types
        """
        return [
            action_type
            for action_type in proposal.get_action_types()
            if ActionRiskClassification.is_irreversible(action_type)
        ]


class HarnessGate:
    """Enforces safety invariants on all proposals.
    
    The HarnessGate is the enforcement layer that sits between the
    PolicyEngine and action execution. Every proposal must pass through
    the gate before actions can be executed.
    
    Enforcement Flow:
        1. Check budget exhaustion → reject if exhausted
        2. Check approval requirements → reject if missing
        3. Check verification evidence → reject if unverified
        4. Add warnings for irreversible actions
    
    Example:
        >>> gate = HarnessGate()
        >>> result = gate.enforce(proposal)
        >>> if not result.valid:
        ...     print(f"Rejected: {result.errors}")
    """
    
    _POLICY_ID = "harness_invariants"
    
    def __init__(self, invariants: HarnessInvariants | None = None) -> None:
        """Initialize the harness gate.
        
        Args:
            invariants: Custom invariants instance (uses default if None)
        """
        self._invariants = invariants or HarnessInvariants()
    
    def enforce(self, proposal: "StepProposal") -> ValidationResult:
        """Enforce all safety invariants on a proposal.
        
        Args:
            proposal: The step proposal to validate
            
        Returns:
            ValidationResult with valid=True if all checks pass,
            or valid=False with error details if any check fails
        """
        errors: list[str] = []
        warnings: list[str] = []
        
        # 1. Check budget exhaustion (highest priority - stop immediately)
        if self._invariants.budget_exhausted(proposal):
            errors.append(self._format_rejection(
                reason_code="BUDGET_EXHAUSTED",
                blocked_action_type=self._first_action_type(proposal) or "HALT",
                blocked_action_risk=self._proposal_risk(proposal),
                remediation_hints=[
                    "Stop execution and request additional budget approval",
                    "Summarize progress before exiting",
                    "Consider breaking task into smaller pieces",
                ],
            ))
            return self._build_result(valid=False, errors=errors, warnings=warnings)
        
        # 2. Check approval requirements
        missing_approvals = self._invariants.get_missing_approvals(proposal)
        if missing_approvals:
            errors.append(self._format_rejection(
                reason_code="APPROVAL_REQUIRED",
                blocked_action_type=missing_approvals[0],
                blocked_action_risk=self._proposal_risk(proposal),
                remediation_hints=[
                    f"Add a REQUEST_APPROVAL action before '{missing_approvals[0]}'",
                    "High-risk operations require explicit user approval",
                    "Wait for approval before proceeding",
                ],
                details={"missing_approvals": missing_approvals},
            ))
            return self._build_result(valid=False, errors=errors, warnings=warnings)
        
        # 3. Check irreversible action warnings (not blocking, just warning)
        irreversible = self._invariants.get_irreversible_actions(proposal)
        if irreversible:
            warnings.append(json.dumps({
                "warning_type": "IRREVERSIBLE_ACTION",
                "message": "This proposal contains irreversible actions",
                "actions": irreversible,
                "recommendation": "Ensure user has explicitly confirmed this operation",
            }))
        
        # 4. Check verification before done
        if not self._invariants.verify_before_done(proposal):
            errors.append(self._format_rejection(
                reason_code="UNVERIFIED_COMPLETION",
                blocked_action_type="COMPLETE_TODO",
                blocked_action_risk=self._proposal_risk(proposal),
                remediation_hints=[
                    f"Provide verification evidence: {list(self._invariants._VERIFICATION_EVIDENCE_TYPES)}",
                    "Include evidence references for completed work",
                    "Ensure all success_criteria are satisfied",
                ],
            ))
            return self._build_result(valid=False, errors=errors, warnings=warnings)
        
        return self._build_result(valid=True, errors=errors, warnings=warnings)
    
    @staticmethod
    def _build_result(
        valid: bool,
        errors: list[str],
        warnings: list[str],
    ) -> ValidationResult:
        """Build a validation result."""
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)
    
    def _format_rejection(
        self,
        reason_code: str,
        blocked_action_type: str,
        blocked_action_risk: str,
        remediation_hints: list[str],
        details: dict | None = None,
    ) -> str:
        """Format a rejection message with structured data.
        
        Args:
            reason_code: Machine-readable rejection code
            blocked_action_type: The action that was blocked
            blocked_action_risk: Risk level of blocked action
            remediation_hints: Suggestions for fixing the issue
            details: Additional structured details
            
        Returns:
            JSON-formatted rejection message
        """
        payload = {
            "policy_id": self._POLICY_ID,
            "reason_code": reason_code,
            "blocked_action_type": blocked_action_type,
            "blocked_action_risk": blocked_action_risk,
            "remediation_hints": remediation_hints,
        }
        if details:
            payload["details"] = details
        return json.dumps(payload)
    
    @staticmethod
    def _proposal_risk(proposal: "StepProposal") -> str:
        """Get risk level string from proposal."""
        risk_level = getattr(proposal, 'risk_level', None)
        return getattr(risk_level, "value", str(risk_level)) if risk_level else "UNKNOWN"
    
    @staticmethod
    def _first_action_type(proposal: "StepProposal") -> str | None:
        """Get first action type from proposal."""
        action_types = proposal.get_action_types()
        return action_types[0] if action_types else None


__all__ = ["HarnessInvariants", "HarnessGate"]
```

---

### 3. Success Criteria Enforcement

**Problem:** Tasks can be marked complete without evidence of success.

**Solution:** Require explicit success criteria and evidence via `StepProposal`.

#### 3.1 Extend StepProposal

**File:** `dawn_kestrel/policy/contracts.py`

Add after `RiskLevel` class:

```python
import pydantic as pd
from pydantic import Field
from typing import Literal


class SuccessCriterion(pd.BaseModel):
    """A single verifiable success criterion.
    
    Success criteria define what "done" looks like for a task.
    Each criterion must be verifiable through one of the defined
    verification methods.
    
    Attributes:
        criterion_id: Unique identifier for this criterion
        description: Human-readable description of success condition
        verification_method: How to verify this criterion is met
        required: Whether this must pass for completion
        verification_command: Optional command to run for verification
    """
    
    criterion_id: str = Field(description="Unique ID for this criterion")
    description: str = Field(description="What success looks like")
    verification_method: Literal[
        "test", 
        "build", 
        "lint", 
        "type_check", 
        "manual", 
        "lsp_diagnostics", 
        "custom"
    ] = Field(description="How to verify this criterion")
    required: bool = Field(default=True, description="Must pass for completion")
    verification_command: str | None = Field(
        default=None, 
        description="Optional command to run for verification"
    )
    
    model_config = pd.ConfigDict(extra="forbid")
```

Update `StepProposal`:

```python
class StepProposal(pd.BaseModel):
    """Agent's proposed next step with actions and risk assessment.
    
    This is the core data structure for agent decision-making.
    Every action an agent wants to take must be packaged as a
    StepProposal and validated by the policy engine.
    
    Attributes:
        intent: Human-readable description of what this step accomplishes
        target_todo_ids: IDs of TODOs this step targets
        requested_context: Context requests for information gathering
        actions: List of actions to execute
        completion_claims: Claims about completed work
        success_criteria: Explicit criteria for task completion
        risk_level: Assessed risk level of this proposal
        requires_verification: Whether verification must pass
        estimated_duration_seconds: Estimated time to complete
        notes: Additional notes or explanations
    """
    
    intent: str
    target_todo_ids: list[str] = Field(default_factory=list)
    requested_context: list["ContextRequest"] = Field(default_factory=list)
    actions: list["Action"] = Field(default_factory=list)
    completion_claims: list["TodoCompletionClaim"] = Field(default_factory=list)
    
    # NEW: Success criteria
    success_criteria: list[SuccessCriterion] = Field(
        default_factory=list,
        description="Explicit criteria that must be met for completion"
    )
    
    # NEW: Enhanced risk assessment
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    requires_verification: bool = Field(
        default=False,
        description="Whether verification must pass before marking complete"
    )
    
    # NEW: Estimation
    estimated_duration_seconds: float | None = Field(
        default=None,
        description="Estimated time to complete this step"
    )
    
    # Existing
    notes: str = ""
    
    model_config = pd.ConfigDict(extra="forbid")
    
    def get_action_types(self) -> list[str]:
        """Get list of action types in this proposal."""
        return [getattr(action, "action_type", "UNKNOWN") for action in self.actions]
```

---

### 4. Cost-Based Budget in BudgetInfo

**Problem:** Budget tracking in `BudgetInfo` is iteration/tool-count based, not cost-based.

**Solution:** Extend `BudgetInfo` with cost and token tracking.

#### 4.1 Extend BudgetInfo

**File:** `dawn_kestrel/policy/contracts.py`

```python
class BudgetInfo(pd.BaseModel):
    """Budget constraints and consumption for policy decisions.
    
    BudgetInfo is the single source of truth for all budget-related
    state. It tracks multiple budget dimensions:
    
    - Iteration count (reasoning loops)
    - Tool calls (function invocations)
    - Wall time (elapsed seconds)
    - Subagent calls (delegations)
    - Cost (USD)
    - Tokens (input/output)
    
    All budget fields have both limits (max_*) and consumption (*_consumed).
    """
    
    # Iteration budget
    max_iterations: int = Field(default=100, ge=1)
    iterations_consumed: int = Field(default=0, ge=0)
    
    # Tool call budget
    max_tool_calls: int = Field(default=1000, ge=1)
    tool_calls_consumed: int = Field(default=0, ge=0)
    
    # Wall time budget
    max_wall_time_seconds: float = Field(default=3600.0, ge=1.0)
    wall_time_consumed: float = Field(default=0.0, ge=0.0)
    
    # Subagent budget
    max_subagent_calls: int = Field(default=50, ge=0)
    subagent_calls_consumed: int = Field(default=0, ge=0)
    
    # NEW: Cost budget (USD)
    max_cost_usd: float = Field(
        default=10.0, 
        ge=0.0,
        description="Maximum cost in USD"
    )
    cost_consumed_usd: float = Field(
        default=0.0, 
        ge=0.0,
        description="Cost consumed in USD"
    )
    
    # NEW: Token budget
    max_tokens_input: int = Field(
        default=1_000_000, 
        ge=0,
        description="Maximum input tokens"
    )
    max_tokens_output: int = Field(
        default=100_000, 
        ge=0,
        description="Maximum output tokens"
    )
    tokens_input_consumed: int = Field(default=0, ge=0)
    tokens_output_consumed: int = Field(default=0, ge=0)
    
    # NEW: Cost model (configurable per provider)
    cost_per_1k_tokens_input: float = Field(
        default=0.003,  # $3/1M tokens
        description="Cost per 1000 input tokens in USD"
    )
    cost_per_1k_tokens_output: float = Field(
        default=0.015,  # $15/1M tokens
        description="Cost per 1000 output tokens in USD"
    )
    
    model_config = pd.ConfigDict(extra="forbid")
    
    def consume_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Record token consumption and update cost.
        
        Args:
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens consumed
        """
        self.tokens_input_consumed += input_tokens
        self.tokens_output_consumed += output_tokens
        
        # Calculate and add cost
        input_cost = (input_tokens / 1000) * self.cost_per_1k_tokens_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens_output
        self.cost_consumed_usd += input_cost + output_cost
    
    def is_cost_exceeded(self) -> bool:
        """Check if cost budget is exceeded."""
        return self.cost_consumed_usd >= self.max_cost_usd
    
    def is_token_exceeded(self) -> bool:
        """Check if token budget is exceeded."""
        return (
            self.tokens_input_consumed >= self.max_tokens_input or
            self.tokens_output_consumed >= self.max_tokens_output
        )
    
    def is_any_exceeded(self) -> bool:
        """Check if any budget dimension is exceeded."""
        return (
            self.iterations_consumed >= self.max_iterations or
            self.tool_calls_consumed >= self.max_tool_calls or
            self.wall_time_consumed >= self.max_wall_time_seconds or
            self.subagent_calls_consumed >= self.max_subagent_calls or
            self.is_cost_exceeded() or
            self.is_token_exceeded()
        )
    
    def remaining_cost_usd(self) -> float:
        """Get remaining cost budget in USD."""
        return max(0, self.max_cost_usd - self.cost_consumed_usd)
    
    def cost_utilization_percent(self) -> float:
        """Get cost utilization as percentage (0-100)."""
        if self.max_cost_usd <= 0:
            return 0.0
        return min(100.0, (self.cost_consumed_usd / self.max_cost_usd) * 100)
    
    def is_cost_critical(self, threshold: float = 0.9) -> bool:
        """Check if cost is above threshold (default 90% consumed).
        
        Args:
            threshold: Fraction threshold (0.9 = 90%)
            
        Returns:
            True if cost consumption exceeds threshold
        """
        if self.max_cost_usd <= 0:
            return False
        return self.cost_consumed_usd >= self.max_cost_usd * threshold
    
    def to_summary_dict(self) -> dict[str, Any]:
        """Get summary of budget state for logging/display."""
        return {
            "iterations": f"{self.iterations_consumed}/{self.max_iterations}",
            "tool_calls": f"{self.tool_calls_consumed}/{self.max_tool_calls}",
            "wall_time": f"{self.wall_time_consumed:.1f}s/{self.max_wall_time_seconds:.1f}s",
            "subagents": f"{self.subagent_calls_consumed}/{self.max_subagent_calls}",
            "cost": f"${self.cost_consumed_usd:.2f}/${self.max_cost_usd:.2f}",
            "cost_percent": f"{self.cost_utilization_percent():.1f}%",
            "tokens_input": f"{self.tokens_input_consumed:,}/{self.max_tokens_input:,}",
            "tokens_output": f"{self.tokens_output_consumed:,}/{self.max_tokens_output:,}",
        }
```

#### 4.2 Wire BudgetInfo Consumption in AgentRuntime

**File:** `dawn_kestrel/agents/runtime.py`

Add token tracking to `execute_agent`:

```python
# In execute_agent method, after LLM response:

# Track token usage
if hasattr(response, 'usage') and response.usage:
    budget_info.consume_tokens(
        input_tokens=response.usage.prompt_tokens or 0,
        output_tokens=response.usage.completion_tokens or 0,
    )

# Check budget thresholds
if budget_info.is_cost_critical(threshold=0.9):
    await bus.publish(
        Events.COST_THRESHOLD_REACHED,
        {
            "session_id": session_id,
            "consumed": budget_info.cost_consumed_usd,
            "limit": budget_info.max_cost_usd,
            "percent": budget_info.cost_utilization_percent(),
        },
    )
```

---

### 5. Consecutive Failure Enforcement (3-Strike Rule)

**Problem:** 3-strike failure rule is prompt-based, not programmatic.

**Solution:** Implement at `AgentRuntime` level with policy integration.

#### 5.1 Failure Tracking Module

**File:** `dawn_kestrel/agents/failure_tracking.py` (new file)

```python
"""Consecutive failure tracking for 3-strike rule enforcement.

This module provides programmatic enforcement of the 3-strike rule:
after 3 consecutive failures, execution halts and escalation is triggered.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Any

from dawn_kestrel.core.event_bus import bus, Events


class FailureSeverity(str, Enum):
    """Severity level for execution failures."""
    
    TRANSIENT = "transient"      # May succeed on retry (timeout, rate limit)
    RECOVERABLE = "recoverable"  # Can continue with alternative approach
    FATAL = "fatal"             # Requires escalation


@dataclass
class FailureRecord:
    """Record of a single execution failure."""
    
    timestamp: float
    action_type: str
    error_message: str
    error_type: str
    severity: FailureSeverity
    context: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "severity": self.severity.value,
            "context": self.context,
        }


@dataclass
class FailureState:
    """Tracks consecutive failures for 3-strike rule.
    
    The failure state tracks:
    - Consecutive failure count (resets on success)
    - Total failure count (never resets)
    - Recent failure history (for debugging)
    
    Strike Counting Rules:
    - FATAL failures count as 1.0 strike
    - RECOVERABLE failures count as 0.5 strike
    - TRANSIENT failures count as 0 strike (they're expected)
    """
    
    consecutive_failures: float = 0.0
    total_failures: int = 0
    last_failure: FailureRecord | None = None
    failure_history: list[FailureRecord] = field(default_factory=list)
    max_history: int = 100
    
    def record_failure(
        self,
        action_type: str,
        error: Exception,
        severity: FailureSeverity = FailureSeverity.TRANSIENT,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a failure and update counters.
        
        Args:
            action_type: Type of action that failed
            error: The exception that was raised
            severity: Severity classification
            context: Additional context about the failure
        """
        record = FailureRecord(
            timestamp=time.time(),
            action_type=action_type,
            error_message=str(error),
            error_type=type(error).__name__,
            severity=severity,
            context=context or {},
        )
        
        self.failure_history.append(record)
        self.last_failure = record
        self.total_failures += 1
        
        # Trim history
        if len(self.failure_history) > self.max_history:
            self.failure_history = self.failure_history[-self.max_history:]
        
        # Update consecutive count based on severity
        if severity == FailureSeverity.FATAL:
            self.consecutive_failures += 1.0
        elif severity == FailureSeverity.RECOVERABLE:
            self.consecutive_failures += 0.5
        # TRANSIENT doesn't increment
    
    def reset_consecutive(self) -> None:
        """Reset consecutive failure count after success."""
        self.consecutive_failures = 0.0
    
    def is_limit_reached(self, limit: int = 3) -> bool:
        """Check if consecutive failure limit is reached.
        
        Args:
            limit: Maximum allowed consecutive failures
            
        Returns:
            True if limit is reached or exceeded
        """
        return self.consecutive_failures >= limit
    
    def get_recent_failures(self, count: int = 3) -> list[FailureRecord]:
        """Get most recent failures.
        
        Args:
            count: Number of failures to return
            
        Returns:
            List of most recent failure records
        """
        return self.failure_history[-count:]
    
    def to_summary(self) -> dict[str, Any]:
        """Get summary of failure state."""
        return {
            "consecutive_failures": self.consecutive_failures,
            "total_failures": self.total_failures,
            "last_failure": self.last_failure.to_dict() if self.last_failure else None,
            "recent_failures": [f.to_dict() for f in self.get_recent_failures()],
        }


class ConsecutiveFailureError(Exception):
    """Raised when consecutive failure limit is reached.
    
    This error indicates that the agent has failed too many times
    in a row and should stop execution. The error includes:
    - Failure state for debugging
    - Whether rollback was possible
    - Last 3 failures for context
    """
    
    def __init__(
        self,
        message: str,
        failure_state: FailureState,
        rollback_performed: bool = False,
    ):
        super().__init__(message)
        self.failure_state = failure_state
        self.rollback_performed = rollback_performed
        self.last_failures = failure_state.get_recent_failures()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": "ConsecutiveFailureError",
            "message": str(self),
            "rollback_performed": self.rollback_performed,
            "failure_state": self.failure_state.to_summary(),
        }


class FailureTracker:
    """Manages failure tracking and 3-strike enforcement.
    
    The FailureTracker is responsible for:
    - Recording failures with severity classification
    - Detecting when the 3-strike limit is reached
    - Triggering rollback callbacks
    - Emitting events for monitoring
    
    Usage:
        tracker = FailureTracker(max_consecutive=3)
        
        try:
            result = await execute_action()
            tracker.record_success()
        except Exception as e:
            tracker.record_failure("EXECUTE_ACTION", e)
            if tracker.is_limit_reached():
                await tracker.handle_limit_reached()
    """
    
    def __init__(
        self,
        max_consecutive: int = 3,
        rollback_callback: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the failure tracker.
        
        Args:
            max_consecutive: Maximum consecutive failures before escalation
            rollback_callback: Async function to call for rollback
        """
        self.max_consecutive = max_consecutive
        self.rollback_callback = rollback_callback
        self.state = FailureState()
    
    def classify_severity(self, error: Exception) -> FailureSeverity:
        """Classify an error's severity for strike counting.
        
        Classification rules:
        - FATAL: Permission errors, syntax errors, critical missing deps
        - TRANSIENT: Timeouts, connection errors, rate limits
        - RECOVERABLE: Everything else
        
        Args:
            error: The exception to classify
            
        Returns:
            FailureSeverity classification
        """
        error_type = type(error).__name__
        
        # Fatal errors - always count as full strike
        fatal_patterns = {
            "PermissionError",
            "FileNotFoundError",
            "SyntaxError",
            "IndentationError",
            "ImportError",
            "ModuleNotFoundError",
        }
        if error_type in fatal_patterns:
            return FailureSeverity.FATAL
        
        # Transient errors - don't count as strike
        transient_patterns = {
            "TimeoutError",
            "ConnectionError",
            "ConnectionRefusedError",
            "ConnectionResetError",
            "RateLimitError",
            "TooManyRequestsError",
        }
        if error_type in transient_patterns:
            return FailureSeverity.TRANSIENT
        
        # Default to recoverable (half strike)
        return FailureSeverity.RECOVERABLE
    
    def record_failure(
        self,
        action_type: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a failure.
        
        Args:
            action_type: Type of action that failed
            error: The exception
            context: Additional context
        """
        severity = self.classify_severity(error)
        self.state.record_failure(action_type, error, severity, context)
    
    def record_success(self) -> None:
        """Record a successful action (resets consecutive count)."""
        self.state.reset_consecutive()
    
    def is_limit_reached(self) -> bool:
        """Check if consecutive failure limit is reached."""
        return self.state.is_limit_reached(self.max_consecutive)
    
    async def handle_limit_reached(self, session_id: str | None = None) -> None:
        """Handle reaching the consecutive failure limit.
        
        This method:
        1. Logs detailed failure information
        2. Attempts rollback if callback is registered
        3. Emits CONSECUTIVE_FAILURE_LIMIT event
        4. Raises ConsecutiveFailureError
        
        Args:
            session_id: Optional session ID for event correlation
            
        Raises:
            ConsecutiveFailureError: Always raised after handling
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Log detailed failure information
        logger.error(
            f"Consecutive failure limit reached ({self.max_consecutive}). "
            f"Failures: {[f.error_message for f in self.state.get_recent_failures()]}"
        )
        
        # 2. Attempt rollback if callback is registered
        rollback_performed = False
        if self.rollback_callback:
            try:
                await self.rollback_callback()
                rollback_performed = True
                logger.info("Rollback callback executed successfully")
            except Exception as rollback_error:
                logger.error(f"Rollback callback failed: {rollback_error}")
        
        # 3. Emit event for monitoring
        event_data = {
            "consecutive_failures": self.state.consecutive_failures,
            "max_consecutive": self.max_consecutive,
            "total_failures": self.state.total_failures,
            "recent_failures": [f.to_dict() for f in self.state.get_recent_failures()],
            "rollback_performed": rollback_performed,
        }
        if session_id:
            event_data["session_id"] = session_id
        
        await bus.publish(Events.CONSECUTIVE_FAILURE_LIMIT, event_data)
        
        # 4. Raise error with recovery context
        raise ConsecutiveFailureError(
            message=f"Consecutive failure limit ({self.max_consecutive}) reached. "
                   f"Last error: {self.state.last_failure.error_message if self.state.last_failure else 'Unknown'}",
            failure_state=self.state,
            rollback_performed=rollback_performed,
        )


__all__ = [
    "FailureSeverity",
    "FailureRecord",
    "FailureState",
    "ConsecutiveFailureError",
    "FailureTracker",
]
```

#### 5.2 Integrate into AgentRuntime

**File:** `dawn_kestrel/agents/runtime.py`

```python
from dawn_kestrel.agents.failure_tracking import FailureTracker, ConsecutiveFailureError

class AgentRuntime:
    """Execute agents with tool filtering and lifecycle management."""
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        base_dir: Path,
        skill_max_char_budget: int | None = None,
        session_lifecycle: SessionLifecycle | None = None,
        provider_registry: ProviderRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        evaluation_hooks: EvaluationHooks | None = None,
        # NEW:
        max_consecutive_failures: int = 3,
        rollback_callback: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        # ... existing init ...
        
        # NEW: Initialize failure tracker
        self._failure_tracker = FailureTracker(
            max_consecutive=max_consecutive_failures,
            rollback_callback=rollback_callback,
        )
    
    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        session_manager: SessionManagerLike,
        tools: ToolRegistry | None,
        skills: list[str],
        options: dict[str, Any] | None = None,
        task_id: str | None = None,
        session_lifecycle: SessionLifecycle | None = None,
    ) -> AgentResult:
        """Execute an agent with tool filtering and lifecycle management."""
        
        # ... existing setup code ...
        
        try:
            # ... existing execution loop ...
            
            # On successful action:
            self._failure_tracker.record_success()
            
        except ConsecutiveFailureError:
            # Re-raise without wrapping
            raise
            
        except Exception as e:
            # Record failure
            self._failure_tracker.record_failure(
                action_type="agent_execution",
                error=e,
                context={"agent_name": agent_name, "session_id": session_id},
            )
            
            # Check 3-strike rule
            if self._failure_tracker.is_limit_reached():
                await self._failure_tracker.handle_limit_reached(session_id)
            
            raise
```

#### 5.3 Add Event Type

**File:** `dawn_kestrel/core/event_bus.py`

```python
class Events:
    # ... existing events ...
    
    # NEW: Failure tracking events
    CONSECUTIVE_FAILURE_LIMIT = "consecutive_failure_limit"
    ROLLBACK_EXECUTED = "rollback_executed"
    
    # NEW: Budget events
    COST_THRESHOLD_REACHED = "cost_threshold_reached"
    TOKEN_THRESHOLD_REACHED = "token_threshold_reached"
    BUDGET_EXHAUSTED = "budget_exhausted"
    
    # NEW: Safety events
    IRREVERSIBLE_ACTION_BLOCKED = "irreversible_action_blocked"
    APPROVAL_REQUIRED = "approval_required"
    VERIFICATION_FAILED = "verification_failed"
```

---

### 6. Strict Policy Implementation

**Problem:** Need a policy that enforces all safety rules strictly.

**Solution:** Create `StrictPolicy` that combines all safety checks.

#### 6.1 Create StrictPolicy

**File:** `dawn_kestrel/policy/strict_policy.py` (new file)

```python
"""Strict policy engine with full safety enforcement.

This policy enforces all safety rules:
- Risk classification
- Approval gates
- Verification requirements
- Budget limits
- Failure tracking

Use this as the default policy for production deployments.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dawn_kestrel.policy.contracts import (
    PolicyInput,
    RiskLevel,
    StepProposal,
    TodoCompletionClaim,
    RequestApprovalAction,
)
from dawn_kestrel.policy.engine import ProposalRejected
from dawn_kestrel.policy.invariants import HarnessGate
from dawn_kestrel.policy.risk_classification import ActionRiskClassification

if TYPE_CHECKING:
    from dawn_kestrel.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)


class StrictPolicy:
    """Strict policy engine with comprehensive safety enforcement.
    
    This policy:
    1. Validates all proposals through HarnessGate
    2. Rejects proposals that violate safety rules
    3. Automatically injects approval requests for high-risk actions
    4. Enforces budget limits
    5. Requires verification evidence for completion claims
    
    Use Cases:
    - Production deployments
    - High-stakes automation
    - Regulated environments
    
    Example:
        >>> policy = StrictPolicy()
        >>> proposal = policy.propose(PolicyInput(goal="Fix bug"))
        >>> if any(a.action_type == "REQUEST_APPROVAL" for a in proposal.actions):
        ...     print("Approval required before proceeding")
    """
    
    def __init__(self, gate: HarnessGate | None = None) -> None:
        """Initialize strict policy.
        
        Args:
            gate: Custom HarnessGate instance (uses default if None)
        """
        self._gate = gate or HarnessGate()
    
    def propose(self, input: PolicyInput) -> StepProposal:
        """Evaluate input and return an approved step proposal.
        
        This method:
        1. Checks budget limits
        2. Validates existing proposals
        3. Injects required approvals
        4. Validates completion claims
        
        Args:
            input: Current runtime state
            
        Returns:
            Approved StepProposal
            
        Raises:
            ProposalRejected: If proposal violates safety rules
        """
        # 1. Check budget
        if input.budgets and input.budgets.is_any_exceeded():
            return self._create_budget_exhausted_proposal(input)
        
        # 2. Check for cost warning (90% consumed)
        if input.budgets and input.budgets.is_cost_critical(threshold=0.9):
            logger.warning(
                f"Cost budget at {input.budgets.cost_utilization_percent():.1f}%"
            )
        
        # 3. Process active TODOs
        if not input.active_todos:
            return self._create_no_todos_proposal(input)
        
        # 4. Get first pending TODO
        first_pending = self._get_first_pending(input.active_todos)
        if not first_pending:
            return self._create_no_pending_proposal(input)
        
        # 5. Create proposal targeting the TODO
        proposal = self._create_targeted_proposal(first_pending, input)
        
        # 6. Validate through harness gate
        validation = self._gate.enforce(proposal)
        
        if not validation.valid:
            raise ProposalRejected(
                reason=self._format_rejection_reason(validation.errors),
                feedback={"errors": validation.errors, "warnings": validation.warnings},
                retry_allowed=True,
            )
        
        # 7. Log warnings
        for warning in validation.warnings:
            logger.warning(f"Safety warning: {warning}")
        
        return proposal
    
    def _get_first_pending(self, todos: list) -> None:
        """Get first pending TODO by priority."""
        pending = [t for t in todos if t.status == "pending"]
        if not pending:
            return None
        
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending.sort(key=lambda t: priority_order.get(t.priority, 1))
        return pending[0]
    
    def _create_budget_exhausted_proposal(self, input: PolicyInput) -> StepProposal:
        """Create proposal indicating budget exhaustion."""
        return StepProposal(
            intent="Budget exhausted - no further actions possible",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
            notes="budget_exhausted",
        )
    
    def _create_no_todos_proposal(self, input: PolicyInput) -> StepProposal:
        """Create proposal when no TODOs exist."""
        return StepProposal(
            intent="No active TODOs - plan generation needed",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
        )
    
    def _create_no_pending_proposal(self, input: PolicyInput) -> StepProposal:
        """Create proposal when no pending TODOs exist."""
        return StepProposal(
            intent="All TODOs completed or blocked",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
        )
    
    def _create_targeted_proposal(self, todo, input: PolicyInput) -> StepProposal:
        """Create proposal targeting a specific TODO."""
        actions = []
        
        # Determine if approval is needed
        # (In a real implementation, we'd analyze the TODO to determine actions)
        # For now, we add a placeholder that will be validated
        
        return StepProposal(
            intent=f"Execute: {todo.description}",
            target_todo_ids=[todo.id],
            requested_context=[],
            actions=actions,
            completion_claims=[],
            risk_level=RiskLevel.MED,  # Default to MED, will be validated
            success_criteria=[],
        )
    
    def _format_rejection_reason(self, errors: list[str]) -> str:
        """Format rejection reason from errors."""
        if not errors:
            return "Unknown validation error"
        
        # Parse first error for cleaner message
        first_error = errors[0]
        try:
            import json
            parsed = json.loads(first_error)
            return f"{parsed.get('reason_code', 'REJECTED')}: {parsed.get('remediation_hints', ['No hints'])[0]}"
        except (json.JSONDecodeError, TypeError):
            return first_error


__all__ = ["StrictPolicy"]
```

#### 6.2 Update RouterPolicy to Include StrictPolicy

**File:** `dawn_kestrel/policy/router_policy.py`

```python
from dawn_kestrel.policy.strict_policy import StrictPolicy

class RouterPolicy:
    def __init__(self) -> None:
        self._rules = RulesPolicy()
        self._react = ReActPolicy()
        self._plan_execute = PlanExecutePolicy()
        self._strict = StrictPolicy()  # NEW
        # Remove: self._fsm = FSMPolicy()
    
    def _get_policy_by_name(self, mode: str) -> PolicyEngine:
        """Get a policy instance by name."""
        policies = {
            "rules": self._rules,
            "react": self._react,
            "plan_execute": self._plan_execute,
            "strict": self._strict,  # NEW
            # Remove "fsm" entry
        }
        return policies.get(mode.lower(), self._strict)  # Default to strict
    
    def _select_policy(self, input: PolicyInput) -> PolicyEngine:
        """Select policy based on signals."""
        # Priority 1: Explicit mode
        policy_mode = os.getenv("DK_POLICY_MODE")
        if policy_mode:
            return self._get_policy_by_name(policy_mode)
        
        # Priority 2: Budget pressure
        if input.budgets and self._compute_budget_headroom(input) <= 0.2:
            return self._strict  # Use strict when budget is low
        
        # Priority 3: Strictness (hard constraints)
        if self._compute_strictness(input) > 0.0:
            return self._strict
        
        # Default to strict (changed from rules)
        return self._strict
```

---

## Implementation Plan

### Phase 1: Core Safety (Week 1)

| Task | File | Effort |
|------|------|--------|
| Enable policy engine by default | `agents/runtime.py` | 0.5 day |
| Add SafetySettings | `core/settings.py` | 0.5 day |
| Add new event types | `core/event_bus.py` | 0.5 day |
| Create `risk_classification.py` | `policy/risk_classification.py` | 1 day |
| **Tests** | `tests/policy/test_risk_classification.py` | 1 day |

### Phase 2: Budget & Cost (Week 2)

| Task | File | Effort |
|------|------|--------|
| Extend `BudgetInfo` | `policy/contracts.py` | 1 day |
| Wire token tracking | `agents/runtime.py` | 1 day |
| Add cost threshold events | `agents/runtime.py` | 0.5 day |
| **Tests** | `tests/policy/test_contracts.py` | 1 day |

### Phase 3: Success Criteria (Week 3)

| Task | File | Effort |
|------|------|--------|
| Add `SuccessCriterion` model | `policy/contracts.py` | 1 day |
| Extend `StepProposal` | `policy/contracts.py` | 0.5 day |
| Update `HarnessGate.enforce()` | `policy/invariants.py` | 1 day |
| **Tests** | `tests/policy/test_invariants.py` | 1 day |

### Phase 4: Failure Tracking (Week 4)

| Task | File | Effort |
|------|------|--------|
| Create `failure_tracking.py` | `agents/failure_tracking.py` | 1 day |
| Integrate into `AgentRuntime` | `agents/runtime.py` | 1 day |
| Add rollback callback support | `agents/runtime.py` | 0.5 day |
| **Tests** | `tests/agents/test_failure_tracking.py` | 1 day |

### Phase 5: Strict Policy (Week 5)

| Task | File | Effort |
|------|------|--------|
| Create `strict_policy.py` | `policy/strict_policy.py` | 1 day |
| Update `RouterPolicy` | `policy/router_policy.py` | 0.5 day |
| Remove FSM fallback | `policy/router_policy.py` | 0.5 day |
| **Tests** | `tests/policy/test_strict_policy.py` | 1 day |

### Phase 6: Documentation (Week 6)

| Task | Effort |
|------|--------|
| Update API documentation | 1 day |
| Write migration guide | 1 day |
| Create configuration examples | 0.5 day |

---

## Test Requirements

### Unit Tests

```python
# tests/policy/test_risk_classification.py

def test_classify_irreversible_action():
    from dawn_kestrel.policy.risk_classification import ActionRiskClassification
    from dawn_kestrel.policy.contracts import RiskLevel
    
    assert ActionRiskClassification.classify("DELETE_FILE") == RiskLevel.CRITICAL
    assert ActionRiskClassification.classify("GIT_PUSH") == RiskLevel.CRITICAL
    assert ActionRiskClassification.classify("GIT_FORCE_PUSH") == RiskLevel.CRITICAL

def test_classify_high_risk_action():
    assert ActionRiskClassification.classify("EDIT_FILE") == RiskLevel.HIGH
    assert ActionRiskClassification.classify("GIT_COMMIT") == RiskLevel.HIGH
    assert ActionRiskClassification.classify("EXECUTE_SHELL") == RiskLevel.HIGH

def test_classify_medium_risk_action():
    assert ActionRiskClassification.classify("RUN_TESTS") == RiskLevel.MED
    assert ActionRiskClassification.classify("RUN_BUILD") == RiskLevel.MED

def test_classify_low_risk_action():
    assert ActionRiskClassification.classify("READ_FILE") == RiskLevel.LOW
    assert ActionRiskClassification.classify("SEARCH_REPO") == RiskLevel.LOW

def test_requires_approval():
    assert ActionRiskClassification.requires_approval("EDIT_FILE") is True
    assert ActionRiskClassification.requires_approval("READ_FILE") is False
    assert ActionRiskClassification.requires_approval("GIT_PUSH") is True

def test_is_irreversible():
    assert ActionRiskClassification.is_irreversible("DELETE_FILE") is True
    assert ActionRiskClassification.is_irreversible("EDIT_FILE") is False
```

```python
# tests/policy/test_budget_info.py

def test_budget_info_cost_tracking():
    from dawn_kestrel.policy.contracts import BudgetInfo
    
    budget = BudgetInfo(
        max_cost_usd=1.0,
        cost_per_1k_tokens_input=0.003,
        cost_per_1k_tokens_output=0.015,
    )
    
    budget.consume_tokens(input_tokens=100000, output_tokens=10000)
    
    assert budget.tokens_input_consumed == 100000
    assert budget.tokens_output_consumed == 10000
    # Cost: (100k/1k * 0.003) + (10k/1k * 0.015) = 0.30 + 0.15 = 0.45
    assert abs(budget.cost_consumed_usd - 0.45) < 0.01

def test_budget_info_exceeded():
    budget = BudgetInfo(max_cost_usd=0.10)
    budget.consume_tokens(input_tokens=100000, output_tokens=10000)
    
    assert budget.is_cost_exceeded() is True

def test_budget_info_critical_threshold():
    budget = BudgetInfo(max_cost_usd=1.0)
    budget.consume_tokens(input_tokens=200000, output_tokens=50000)
    
    # Consumed: (200k/1k * 0.003) + (50k/1k * 0.015) = 0.60 + 0.75 = 1.35
    assert budget.is_cost_critical(threshold=0.5) is True
```

```python
# tests/agents/test_failure_tracking.py

import pytest
from dawn_kestrel.agents.failure_tracking import (
    FailureState,
    FailureSeverity,
    FailureTracker,
    ConsecutiveFailureError,
)


def test_failure_state_tracking():
    state = FailureState()
    state.record_failure("EDIT_FILE", Exception("Error"), FailureSeverity.FATAL)
    
    assert state.consecutive_failures == 1.0
    assert state.total_failures == 1


def test_failure_severity_weighting():
    state = FailureState()
    
    # FATAL = 1.0 strike
    state.record_failure("A", Exception("1"), FailureSeverity.FATAL)
    assert state.consecutive_failures == 1.0
    
    # RECOVERABLE = 0.5 strike
    state.record_failure("B", Exception("2"), FailureSeverity.RECOVERABLE)
    assert state.consecutive_failures == 1.5
    
    # TRANSIENT = 0 strike
    state.record_failure("C", Exception("3"), FailureSeverity.TRANSIENT)
    assert state.consecutive_failures == 1.5


def test_consecutive_reset():
    state = FailureState()
    state.record_failure("A", Exception("1"), FailureSeverity.FATAL)
    state.record_failure("A", Exception("2"), FailureSeverity.FATAL)
    assert state.consecutive_failures == 2.0
    
    state.reset_consecutive()
    assert state.consecutive_failures == 0.0


def test_three_strike_limit():
    state = FailureState()
    state.record_failure("A", Exception("1"), FailureSeverity.FATAL)
    state.record_failure("A", Exception("2"), FailureSeverity.FATAL)
    state.record_failure("A", Exception("3"), FailureSeverity.FATAL)
    
    assert state.is_limit_reached(limit=3)


@pytest.mark.asyncio
async def test_failure_tracker_limit_handling():
    tracker = FailureTracker(max_consecutive=2)
    
    tracker.record_failure("A", PermissionError("denied"))
    tracker.record_failure("B", PermissionError("denied"))
    
    assert tracker.is_limit_reached()
    
    with pytest.raises(ConsecutiveFailureError) as exc:
        await tracker.handle_limit_reached(session_id="test")
    
    assert exc.value.rollback_performed is False
```

---

## Migration Guide

### Environment Variables

```bash
# Old (opt-in):
DK_POLICY_ENGINE=1

# New (opt-out):
DK_POLICY_ENGINE=0  # Only set to disable
DK_POLICY_MODE=strict  # Options: rules, react, plan_execute, strict
```

### Budget Configuration

```python
# Old:
from dawn_kestrel.core.fsm import FSMBudget
budget = FSMBudget(max_iterations=100)

# New:
from dawn_kestrel.policy.contracts import BudgetInfo
budget = BudgetInfo(
    max_iterations=100,
    max_cost_usd=10.0,  # NEW
    max_tokens_input=1_000_000,  # NEW
)
```

### Event Subscription

```python
from dawn_kestrel.core.event_bus import bus, Events

# Subscribe to new safety events
await bus.subscribe(Events.CONSECUTIVE_FAILURE_LIMIT, on_failure)
await bus.subscribe(Events.COST_THRESHOLD_REACHED, on_cost_warning)
await bus.subscribe(Events.IRREVERSIBLE_ACTION_BLOCKED, on_blocked)
```

---

## Appendix: File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `policy/risk_classification.py` | Action risk classification |
| `policy/strict_policy.py` | Strict policy implementation |
| `agents/failure_tracking.py` | 3-strike rule enforcement |
| `tests/policy/test_risk_classification.py` | Risk classification tests |
| `tests/policy/test_budget_info.py` | Budget tracking tests |
| `tests/agents/test_failure_tracking.py` | Failure tracking tests |

### Modified Files

| File | Changes |
|------|---------|
| `agents/runtime.py` | Policy enablement, failure tracking, token tracking |
| `policy/contracts.py` | RiskLevel, SuccessCriterion, BudgetInfo extensions |
| `policy/invariants.py` | Risk classification integration |
| `policy/router_policy.py` | StrictPolicy integration, FSM removal |
| `core/settings.py` | SafetySettings configuration |
| `core/event_bus.py` | New safety event types |

---

**End of Specification**
