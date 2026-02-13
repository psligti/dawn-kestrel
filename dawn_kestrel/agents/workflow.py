"""Workflow phase output contracts for agent-based orchestration.

Defines Pydantic models for each workflow phase output in the agent harness:
- Intake: intent, constraints, initial evidence snapshot
- Plan: prioritized todo list (create/modify/prioritize)
- Act: actions attempted, tool results summary, artifacts/evidence references
- Synthesize: merged findings + updated todos/statuses
- Check: should_continue, stop_reason, confidence, budget_consumed

All models use extra="forbid" to ensure strict schema compliance for LLM outputs.
Each model provides a get_*_schema() helper returning a strict JSON schema string for prompt inclusion.

The models align with the canonical stop/loop policy in docs/planning-agent-orchestration.md
including budget constraints (iterations, subagent_calls, wall_time) and stop reasons
(recommendation_ready, blocking_question, budget_exhausted, stagnation, human_required).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

import pydantic as pd


class IntakeOutput(pd.BaseModel):
    """Output from the intake phase of the workflow.

    The intake phase captures the initial request, constraints, and evidence snapshot.
    This establishes the triad (goal, constraints, initial evidence) by turn 1.

    Attributes:
        intent: Concise restatement of what the agent is trying to achieve
        constraints: Known limitations (tools, permissions, time, boundaries of scope)
        initial_evidence: What is already known or assumed (from repo snapshot, files, context)
    """

    intent: str
    """Concise restatement of what the agent is trying to achieve"""

    constraints: List[str] = pd.Field(default_factory=list)
    """Known limitations (tools, permissions, time, boundaries of scope)"""

    initial_evidence: List[str] = pd.Field(default_factory=list)
    """What is already known or assumed (from repo snapshot, files, context)"""

    model_config = pd.ConfigDict(extra="forbid")


class TodoItem(pd.BaseModel):
    """A single todo item in the plan.

    Represents a unit of work with operation type, description, priority,
    and current status.

    Attributes:
        id: Unique identifier for this todo item
        operation: Type of operation (create, modify, prioritize, skip)
        description: What needs to be done
        priority: Priority level (high, medium, low)
        status: Current status (pending, in_progress, completed, skipped, blocked)
        dependencies: List of todo item IDs this depends on
        notes: Additional context or rationale
    """

    id: str
    """Unique identifier for this todo item"""

    operation: Literal["create", "modify", "prioritize", "skip"]
    """Type of operation"""

    description: str
    """What needs to be done"""

    priority: Literal["high", "medium", "low"] = "medium"
    """Priority level"""

    status: Literal["pending", "in_progress", "completed", "skipped", "blocked"] = "pending"
    """Current status"""

    dependencies: List[str] = pd.Field(default_factory=list)
    """List of todo item IDs this depends on"""

    notes: str = ""
    """Additional context or rationale"""

    model_config = pd.ConfigDict(extra="forbid")


class PlanOutput(pd.BaseModel):
    """Output from the plan phase of the workflow.

    The plan phase generates/updates/prioritizes todos. This is part of the
    sub-loop (plan → act → synthesize → check) that repeats until stop conditions.

    Attributes:
        todos: Prioritized list of todo items
        reasoning: Rationale for the plan structure
        estimated_iterations: Estimated number of iterations needed
        strategy_selected: Which strategy/approach was chosen
    """

    todos: List[TodoItem] = pd.Field(default_factory=list)
    """Prioritized list of todo items"""

    reasoning: str = ""
    """Rationale for the plan structure"""

    estimated_iterations: int = 1
    """Estimated number of iterations needed"""

    strategy_selected: str = ""
    """Which strategy/approach was chosen"""

    model_config = pd.ConfigDict(extra="forbid")


class ToolExecution(pd.BaseModel):
    """Record of a single tool execution.

    Tracks what tool was called, with what arguments, and the result.

    Attributes:
        tool_name: Name of the tool that was executed
        arguments: Arguments passed to the tool (sanitized)
        status: Status of the execution (success, failure, timeout)
        result_summary: Brief summary of the result
        duration_seconds: Time taken for execution
        artifacts: List of file paths or evidence references created
    """

    tool_name: str
    """Name of the tool that was executed"""

    arguments: Dict[str, Any] = pd.Field(default_factory=dict)
    """Arguments passed to the tool (sanitized)"""

    status: Literal["success", "failure", "timeout"]
    """Status of the execution"""

    result_summary: str = ""
    """Brief summary of the result"""

    duration_seconds: float = 0.0
    """Time taken for execution"""

    artifacts: List[str] = pd.Field(default_factory=list)
    """List of file paths or evidence references created"""

    model_config = pd.ConfigDict(extra="forbid")


class ActOutput(pd.BaseModel):
    """Output from the act phase of the workflow.

    The act phase uses tools to perform work against top-priority todos.
    This is part of the sub-loop (plan → act → synthesize → check).

    Attributes:
        actions_attempted: List of tool executions performed
        todos_addressed: IDs of todo items this act phase addressed
        tool_results_summary: High-level summary of all tool results
        artifacts: List of all artifacts/evidence references created
        failures: List of any failures or errors encountered
    """

    actions_attempted: List[ToolExecution] = pd.Field(default_factory=list)
    """List of tool executions performed"""

    todos_addressed: List[str] = pd.Field(default_factory=list)
    """IDs of todo items this act phase addressed"""

    tool_results_summary: str = ""
    """High-level summary of all tool results"""

    artifacts: List[str] = pd.Field(default_factory=list)
    """List of all artifacts/evidence references created"""

    failures: List[str] = pd.Field(default_factory=list)
    """List of any failures or errors encountered"""

    model_config = pd.ConfigDict(extra="forbid")


class SynthesizedFinding(pd.BaseModel):
    """A finding from the synthesize phase.

    Merged findings from tool results and analysis.

    Attributes:
        id: Unique identifier for this finding
        category: Category of finding (security, performance, correctness, style, etc.)
        severity: Severity level (critical, high, medium, low, info)
        title: Brief title describing the finding
        description: Detailed description of the finding
        evidence: Evidence supporting this finding
        recommendation: Suggested action to address the finding
        confidence: Confidence score (0.0-1.0)
        related_todos: IDs of related todo items
    """

    id: str
    """Unique identifier for this finding"""

    category: Literal[
        "security", "performance", "correctness", "style", "architecture", "documentation", "other"
    ]
    """Category of finding"""

    severity: Literal["critical", "high", "medium", "low", "info"]
    """Severity level"""

    title: str
    """Brief title describing the finding"""

    description: str = ""
    """Detailed description of the finding"""

    evidence: str = ""
    """Evidence supporting this finding"""

    recommendation: str = ""
    """Suggested action to address the finding"""

    confidence: float = 0.5
    """Confidence score (0.0-1.0)"""

    related_todos: List[str] = pd.Field(default_factory=list)
    """IDs of related todo items"""

    model_config = pd.ConfigDict(extra="forbid")

    @pd.field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        """Validate confidence is in 0.0-1.0 range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class SynthesizeOutput(pd.BaseModel):
    """Output from the synthesize phase of the workflow.

    The synthesize phase reviews/merges results and updates todo statuses.
    This is part of the sub-loop (plan → act → synthesize → check).

    Attributes:
        findings: Merged findings from tool results and analysis
        updated_todos: Updated todo items with new statuses
        summary: High-level summary of synthesized results
        uncertainty_reduction: Estimated percentage of uncertainty reduced (0.0-1.0)
        confidence_level: Overall confidence in results (0.0-1.0)
    """

    findings: List[SynthesizedFinding] = pd.Field(default_factory=list)
    """Merged findings from tool results and analysis"""

    updated_todos: List[TodoItem] = pd.Field(default_factory=list)
    """Updated todo items with new statuses"""

    summary: str = ""
    """High-level summary of synthesized results"""

    uncertainty_reduction: float = 0.0
    """Estimated percentage of uncertainty reduced (0.0-1.0)"""

    confidence_level: float = 0.5
    """Overall confidence in results (0.0-1.0)"""

    model_config = pd.ConfigDict(extra="forbid")

    @pd.field_validator("confidence_level")
    @classmethod
    def validate_confidence_level_range(cls, v: float) -> float:
        """Validate confidence_level is in 0.0-1.0 range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence_level must be between 0.0 and 1.0")
        return v


class BudgetConsumed(pd.BaseModel):
    """Budget consumed during workflow execution.

    Tracks resource usage across iterations, subagent calls, and wall time.

    Attributes:
        iterations: Number of iterations executed
        subagent_calls: Number of subagent calls made
        wall_time_seconds: Wall time elapsed in seconds
        tool_calls: Number of tool calls made
        tokens_consumed: Total tokens consumed (if available)
    """

    iterations: int = 0
    """Number of iterations executed"""

    subagent_calls: int = 0
    """Number of subagent calls made"""

    wall_time_seconds: float = 0.0
    """Wall time elapsed in seconds"""

    tool_calls: int = 0
    """Number of tool calls made"""

    tokens_consumed: int = 0
    """Total tokens consumed (if available)"""

    model_config = pd.ConfigDict(extra="forbid")


class CheckOutput(pd.BaseModel):
    """Output from the check phase of the workflow.

    The check phase decides whether to continue the loop, enforcing stop conditions.
    This is part of the sub-loop (plan → act → synthesize → check).

    Aligns with canonical stop/loop policy in docs/planning-agent-orchestration.md:
    - Good stops: recommendation_ready, blocking_question, budget_exhausted
    - Bad stops (avoid): evidence_theater, over_interviewing, premature_commit, unbounded_loop
    - Stop reasons: recommendation_ready, blocking_question, budget_exhausted, stagnation, human_required

    Attributes:
        should_continue: Whether the workflow should continue to next iteration
        stop_reason: Reason for stopping (if should_continue is False)
        confidence: Confidence in current results (0.0-1.0)
        budget_consumed: Budget tracking for all resources
        blocking_question: Optional blocking question if escalation needed
        novelty_detected: Whether new information was discovered this iteration
        stagnation_detected: Whether stagnation was detected (same error, no new files, etc.)
        next_action: Suggested next action (continue, switch_strategy, escalate, commit)
    """

    should_continue: bool
    """Whether the workflow should continue to next iteration"""

    stop_reason: Literal[
        "recommendation_ready",
        "blocking_question",
        "budget_exhausted",
        "stagnation",
        "human_required",
        "risk_threshold",
        "none",
    ] = "none"
    """Reason for stopping (if should_continue is False)"""

    confidence: float = 0.5
    """Confidence in current results (0.0-1.0)"""

    budget_consumed: BudgetConsumed = pd.Field(default_factory=BudgetConsumed)
    """Budget tracking for all resources"""

    @pd.field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        """Validate confidence is in 0.0-1.0 range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    blocking_question: str = ""
    """Optional blocking question if escalation needed"""

    novelty_detected: bool = True
    """Whether new information was discovered this iteration"""

    stagnation_detected: bool = False
    """Whether stagnation was detected (same error, no new files, etc.)"""

    next_action: Literal["continue", "switch_strategy", "escalate", "commit", "stop"] = "continue"
    """Suggested next action"""

    model_config = pd.ConfigDict(extra="forbid")


def get_intake_output_schema() -> str:
    """Return JSON schema for IntakeOutput as a string for inclusion in prompts.

    This schema must match exactly the IntakeOutput Pydantic model above.
    Any changes to the model must be reflected here.

    Returns:
        JSON schema string with explicit type information and strict validation rules
    """
    return f"""You MUST output valid JSON matching this exact schema. The output is parsed directly by IntakeOutput Pydantic model with no post-processing. Do NOT add any fields outside this schema:

{IntakeOutput.model_json_schema()}

CRITICAL RULES:
- Include ALL required fields: intent
- Optional fields (constraints, initial_evidence) can be omitted or empty arrays
- NEVER include extra fields not in this schema (will cause validation errors)
- Return ONLY the JSON object, no other text, no markdown code blocks
- Output must be valid JSON that passes IntakeOutput Pydantic validation as-is

EXAMPLE VALID OUTPUT:
{{
  "intent": "Add JWT authentication to the auth module",
  "constraints": [
    "Cannot access external services",
    "Must complete within 5 iterations",
    "Only have read access to codebase"
  ],
  "initial_evidence": [
    "Auth module exists at src/auth/",
    "Current implementation uses session-based auth from README",
    "No existing JWT integration found"
  ]
}}
"""


def get_plan_output_schema() -> str:
    """Return JSON schema for PlanOutput as a string for inclusion in prompts.

    This schema must match exactly the PlanOutput Pydantic model above.
    Any changes to the model must be reflected here.

    Returns:
        JSON schema string with explicit type information and strict validation rules
    """
    return f"""You MUST output valid JSON matching this exact schema. The output is parsed directly by PlanOutput Pydantic model with no post-processing. Do NOT add any fields outside this schema:

{PlanOutput.model_json_schema()}

CRITICAL RULES:
- Include ALL required fields: todos
- Optional fields (reasoning, estimated_iterations, strategy_selected) have defaults
- NEVER include extra fields not in this schema (will cause validation errors)
- For each todo item, operation must be one of: create, modify, prioritize, skip
- Priority must be one of: high, medium, low
- Status must be one of: pending, in_progress, completed, skipped, blocked
- Return ONLY the JSON object, no other text, no markdown code blocks
- Output must be valid JSON that passes PlanOutput Pydantic validation as-is

EXAMPLE VALID OUTPUT:
{{
  "todos": [
    {{
      "id": "1",
      "operation": "create",
      "description": "Research JWT authentication best practices",
      "priority": "high",
      "status": "pending",
      "dependencies": [],
      "notes": "Must understand JWT patterns before implementation"
    }},
    {{
      "id": "2",
      "operation": "create",
      "description": "Find existing JWT integration tests",
      "priority": "medium",
      "status": "pending",
      "dependencies": ["1"],
      "notes": "Look for tests in tests/auth/"
    }}
  ],
  "reasoning": "Need to understand JWT patterns first, then verify existing implementation",
  "estimated_iterations": 3,
  "strategy_selected": "Documentation-first approach"
}}
"""


def get_act_output_schema() -> str:
    """Return JSON schema for ActOutput as a string for inclusion in prompts.

    This schema must match exactly the ActOutput Pydantic model above.
    Any changes to the model must be reflected here.

    Returns:
        JSON schema string with explicit type information and strict validation rules
    """
    return f"""You MUST output valid JSON matching this exact schema. The output is parsed directly by ActOutput Pydantic model with no post-processing. Do NOT add any fields outside this schema:

{ActOutput.model_json_schema()}

CRITICAL RULES:
- Include ALL required fields: actions_attempted
- Optional fields (todos_addressed, tool_results_summary, artifacts, failures) have defaults
- NEVER include extra fields not in this schema (will cause validation errors)
- For each tool execution, status must be one of: success, failure, timeout
- Return ONLY the JSON object, no other text, no markdown code blocks
- Output must be valid JSON that passes ActOutput Pydantic validation as-is

EXAMPLE VALID OUTPUT:
{{
  "actions_attempted": [
    {{
      "tool_name": "read",
      "arguments": {{"file_path": "src/auth.py"}},
      "status": "success",
      "result_summary": "Read 150 lines from auth module",
      "duration_seconds": 0.5,
      "artifacts": ["src/auth.py"]
    }},
    {{
      "tool_name": "grep",
      "arguments": {{"pattern": "jwt", "path": "src/"}},
      "status": "success",
      "result_summary": "Found 3 files containing jwt",
      "duration_seconds": 1.2,
      "artifacts": []
    }}
  ],
  "todos_addressed": ["1", "2"],
  "tool_results_summary": "Successfully read auth module and found JWT references",
  "artifacts": ["src/auth.py"],
  "failures": []
}}
"""


def get_synthesize_output_schema() -> str:
    """Return JSON schema for SynthesizeOutput as a string for inclusion in prompts.

    This schema must match exactly the SynthesizeOutput Pydantic model above.
    Any changes to the model must be reflected here.

    Returns:
        JSON schema string with explicit type information and strict validation rules
    """
    return f"""You MUST output valid JSON matching this exact schema. The output is parsed directly by SynthesizeOutput Pydantic model with no post-processing. Do NOT add any fields outside this schema:

{SynthesizeOutput.model_json_schema()}

CRITICAL RULES:
- Include ALL required fields: findings, updated_todos
- Optional fields (summary, uncertainty_reduction, confidence_level) have defaults
- NEVER include extra fields not in this schema (will cause validation errors)
- For each finding, category must be one of: security, performance, correctness, style, architecture, documentation, other
- Severity must be one of: critical, high, medium, low, info
- Confidence must be between 0.0 and 1.0
- Return ONLY the JSON object, no other text, no markdown code blocks
- Output must be valid JSON that passes SynthesizeOutput Pydantic validation as-is

EXAMPLE VALID OUTPUT:
{{
  "findings": [
    {{
      "id": "F-001",
      "category": "security",
      "severity": "high",
      "title": "Missing JWT validation",
      "description": "JWT tokens are not validated before use",
      "evidence": "Found JWT use in src/auth.py:45 without validation",
      "recommendation": "Add JWT signature verification before using tokens",
      "confidence": 0.8,
      "related_todos": ["1"]
    }}
  ],
  "updated_todos": [
    {{
      "id": "1",
      "operation": "modify",
      "description": "Research JWT authentication best practices",
      "priority": "high",
      "status": "completed",
      "dependencies": [],
      "notes": "JWT patterns understood"
    }}
  ],
  "summary": "Found security issue with JWT validation",
  "uncertainty_reduction": 0.6,
  "confidence_level": 0.8
}}
"""


def get_check_output_schema() -> str:
    """Return JSON schema for CheckOutput as a string for inclusion in prompts.

    This schema must match exactly the CheckOutput Pydantic model above.
    Any changes to the model must be reflected here.

    Aligns with canonical stop/loop policy in docs/planning-agent-orchestration.md.

    Returns:
        JSON schema string with explicit type information and strict validation rules
    """
    return f"""You MUST output valid JSON matching this exact schema. The output is parsed directly by CheckOutput Pydantic model with no post-processing. Do NOT add any fields outside this schema:

{CheckOutput.model_json_schema()}

 CRITICAL RULES:
- Include ALL required fields: should_continue
- Optional fields (stop_reason, confidence, budget_consumed, blocking_question, novelty_detected, stagnation_detected, next_action) have defaults
- NEVER include extra fields not in this schema (will cause validation errors)
- stop_reason must be one of: recommendation_ready, blocking_question, budget_exhausted, stagnation, human_required, risk_threshold, none
- confidence must be between 0.0 and 1.0
- next_action must be one of: continue, switch_strategy, escalate, commit, stop
- Return ONLY the JSON object, no other text, no markdown code blocks
- Output must be valid JSON that passes CheckOutput Pydantic validation as-is

STOP REASONS (from canonical policy in docs/planning-agent-orchestration.md):
- recommendation_ready: Confidence >= 0.8, implementation path defined, no unanswered blocking questions
- blocking_question: Single question that cannot be answered via available tools, answers fundamental ambiguity
- budget_exhausted: Max iterations/calls/time reached, best effort provided
- stagnation: No new information, same failure signature, confidence plateau
- human_required: Missing information that cannot be obtained with available tools, ambiguous requirement, permission denied, conflicting policies

EXAMPLE VALID OUTPUT (CONTINUE):
{{
  "should_continue": true,
  "stop_reason": "none",
  "confidence": 0.6,
  "budget_consumed": {{
    "iterations": 2,
    "subagent_calls": 4,
    "wall_time_seconds": 45.0,
    "tool_calls": 8,
    "tokens_consumed": 2500
  }},
  "blocking_question": "",
  "novelty_detected": true,
  "stagnation_detected": false,
  "next_action": "continue"
}}

EXAMPLE VALID OUTPUT (RECOMMENDATION READY):
{{
  "should_continue": false,
  "stop_reason": "recommendation_ready",
  "confidence": 0.85,
  "budget_consumed": {{
    "iterations": 4,
    "subagent_calls": 6,
    "wall_time_seconds": 120.0,
    "tool_calls": 12,
    "tokens_consumed": 5000
  }},
  "blocking_question": "",
  "novelty_detected": false,
  "stagnation_detected": false,
  "next_action": "commit"
}}

EXAMPLE VALID OUTPUT (BLOCKING QUESTION):
{{
  "should_continue": false,
  "stop_reason": "blocking_question",
  "confidence": 0.5,
  "budget_consumed": {{
    "iterations": 3,
    "subagent_calls": 5,
    "wall_time_seconds": 90.0,
    "tool_calls": 10,
    "tokens_consumed": 4000
  }},
  "blocking_question": "The auth module supports both JWT and session-based auth. Which should we use for the new API endpoint?",
  "novelty_detected": false,
  "stagnation_detected": false,
  "next_action": "escalate"
}}

EXAMPLE VALID OUTPUT (BUDGET EXHAUSTED):
{{
  "should_continue": false,
  "stop_reason": "budget_exhausted",
  "confidence": 0.7,
  "budget_consumed": {{
    "iterations": 5,
    "subagent_calls": 8,
    "wall_time_seconds": 300.0,
    "tool_calls": 15,
    "tokens_consumed": 6000
  }},
  "blocking_question": "Cannot complete JWT implementation within 5 iterations without more information about existing auth patterns",
  "novelty_detected": false,
  "stagnation_detected": false,
  "next_action": "stop"
}}

EXAMPLE VALID OUTPUT (STAGNATION):
{{
  "should_continue": false,
  "stop_reason": "stagnation",
  "confidence": 0.5,
  "budget_consumed": {{
    "iterations": 3,
    "subagent_calls": 6,
    "wall_time_seconds": 60.0,
    "tool_calls": 8,
    "tokens_consumed": 3000
  }},
  "blocking_question": "",
  "novelty_detected": false,
  "stagnation_detected": true,
  "next_action": "switch_strategy"
}}
"""
