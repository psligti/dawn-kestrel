"""Architecture Reviewer agent for checking architectural issues."""
from __future__ import annotations
from typing import List
import pydantic as pd
import uuid

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Finding,
    MergeGate,
)
from opencode_python.ai_session import AISession
from opencode_python.core.models import Session
from opencode_python.core.settings import settings


class ArchitectureReviewer(BaseReviewerAgent):
    """Reviewer agent specialized in architectural analysis.

    Checks for:
    - Boundary violations (cross-module dependencies)
    - Coupling issues (tight coupling between components)
    - Anti-patterns (god objects, leaky abstractions)
    - Backwards compatibility concerns
    """

    _SYSTEM_PROMPT = """You are the Architecture Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to architecture.
- Decide what checks/tools to run based on what changed; propose minimal targeted checks first.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pyproject.toml, CI workflows, make/just/nox/tox) to propose correct commands.

You specialize in:
- boundaries, layering, dependency direction
- cohesion/coupling, modularity, naming consistency
- data flow correctness (interfaces, contracts, invariants)
- concurrency/async correctness (if applicable)
- config/env separation (settings vs code)
- backwards compatibility and migration concerns
- anti-pattern detection: god objects, leaky abstractions, duplicated logic

Scoping heuristics:
- Relevant when changes include: src/**, app/**, domain/**, services/**, core/**, libs/**,
  API route layers, dependency injection, orchestration layers, agent/skills/tools frameworks.
- Often ignore: docs-only, comments-only, formatting-only changes (unless refactor hides risk).

Checks you may request (only if relevant):
- Type checks (mypy/pyright) when interfaces changed
- Unit tests when behavior changed
- Targeted integration tests when contracts or IO boundaries changed

Architecture review must answer:
1) What is the intended design change?
2) Does the change preserve clear boundaries and a single source of truth?
3) Does it introduce hidden coupling or duplicated logic?
4) Are there new edge cases, failure modes, or lifecycle issues?

Common blocking issues:
- circular dependencies introduced
- public API/contract changed without updating call sites/tests
- configuration hard-coded into business logic
- breaking changes without migration path

Output MUST be valid JSON only with this schema:

{
  "agent": "architecture",
  "summary": "...",
  "severity": "merge|warning|critical|blocking",
  "scope": { "relevant_files": [], "ignored_files": [], "reasoning": "..." },
  "checks": [{ "name": "...", "required": true, "commands": [], "why": "...", "expected_signal": "..." }],
  "skips": [{ "name": "...", "why_safe": "...", "when_to_run": "..." }],
  "findings": [{
    "id": "ARCH-001",
    "title": "...",
    "severity": "warning|critical|blocking",
    "confidence": "high|medium|low",
    "owner": "dev|docs|devops|security",
    "estimate": "S|M|L",
    "evidence": "...",
    "risk": "...",
    "recommendation": "...",
    "suggested_patch": "..."
  }],
  "merge_gate": { "decision": "approve|needs_changes|block", "must_fix": [], "should_fix": [], "notes_for_coding_agent": [] }
}

Rules:
- If there are no relevant files, return severity "merge" and note "no relevant changes".
- Tie every finding to evidence. No vague statements.
- If you recommend skipping a check, explain why it's safe.
Return JSON only.
"""

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "architecture"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer agent."""
        return self._SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return ["**/*.py"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform architectural review on the given context using LLM.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision

        Raises:
            ValueError: If API key is missing or invalid
            TimeoutError: If LLM request times out
            Exception: For other API-related errors
        """
        relevant_files = []
        for file_path in context.changed_files:
            if self.is_relevant_to_changes([file_path]):
                relevant_files.append(file_path)

        provider_id = settings.provider_default
        model = settings.model_default
        api_key = settings.api_key.get_secret_value() if settings.api_key else None

        session = Session(
            id=str(uuid.uuid4()),
            slug="architecture-review",
            project_id="review",
            directory=context.repo_root or "/tmp",
            title="Architecture Review",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id=provider_id,
            model=model,
            api_key=api_key
        )

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes for architectural issues and provide your review in the specified JSON format."""

        try:
            response_message = await ai_session.process_message(
                user_message,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            )

            if not response_message.text:
                raise ValueError("Empty response from LLM")

            try:
                output = ReviewOutput.model_validate_json(response_message.text)
            except pd.ValidationError as e:
                return ReviewOutput(
                    agent=self.get_agent_name(),
                    summary=f"Error parsing LLM response: {str(e)}",
                    severity="critical",
                    scope=Scope(
                        relevant_files=relevant_files,
                        ignored_files=[],
                        reasoning="Failed to parse LLM JSON response due to validation error."
                    ),
                    findings=[],
                    merge_gate=MergeGate(
                        decision="needs_changes",
                        must_fix=[],
                        should_fix=[],
                        notes_for_coding_agent=[
                            "Review LLM response format and ensure it matches expected schema."
                        ]
                    )
                )

            return output

        except (TimeoutError, Exception) as e:
            if isinstance(e, (TimeoutError, ValueError)):
                raise
            raise Exception(f"LLM API error: {str(e)}") from e
