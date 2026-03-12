"""Agent runtime bridge for transforming AgentResult to ReviewOutput.

This module provides the agent_result_to_review_output function that handles
the transformation from AgentRuntime's AgentResult to the review agent's
ReviewOutput contract.

The transformation includes:
1. Extracting JSON from the agent's response (plain JSON or markdown-wrapped)
2. Parsing and validating the JSON against ReviewOutput schema
3. Handling edge cases (empty response, invalid JSON, missing fields)
4. Returning appropriate defaults when JSON extraction fails
"""

from __future__ import annotations

import json
import logging
import re

from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import MergeDecision, MergeGate, ReviewOutput, Scope, Severity
from dawn_kestrel.core.agent_types import AgentResult

logger = logging.getLogger(__name__)


def extract_json_from_response(response: str) -> str | None:
    """Extract JSON from agent response, handling markdown code blocks.

    Args:
        response: Raw text response from the agent

    Returns:
        JSON string if found, None otherwise
    """
    if not response or not response.strip():
        return None

    response = response.strip()

    # Try to parse as plain JSON first
    try:
        json.loads(response)
        return response
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    patterns = [
        r"```(?:json)?\s*([\s\S]*?)\s*```",  # ```json ... ``` or ``` ... ```
        r"```\s*([\s\S]*?)\s*```",  # ``` ... ```
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue

    # Try to find JSON-like object in the response
    # Look for patterns like {...} that might be JSON
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_pattern, response, re.MULTILINE | re.DOTALL)
    for match in matches:
        try:
            json.loads(match)
            return match
        except json.JSONDecodeError:
            continue

    return None


def agent_result_to_review_output(
    agent_result: AgentResult,
    context: ReviewContext,
) -> ReviewOutput:
    """Transform AgentResult from AgentRuntime to ReviewOutput.

    This function:
    1. Extracts JSON from AgentResult.response
    2. Validates JSON against ReviewOutput schema
    3. Handles edge cases (empty, invalid JSON, missing fields)
    4. Returns defaults when transformation fails

    Args:
        agent_result: Result from AgentRuntime.execute_agent()
        context: ReviewContext with changed files and metadata

    Returns:
        ReviewOutput with findings, severity, and merge gate decision

    Raises:
        ValueError: If agent_result.error is set (execution failure)
    """
    if agent_result.error:
        raise ValueError(f"Agent execution failed: {agent_result.error}")

    logger.debug(f"Transforming AgentResult from agent: {agent_result.agent_name}")
    logger.debug(f"Response length: {len(agent_result.response)} chars")
    logger.debug(f"Tools used: {agent_result.tools_used}")
    logger.debug(f"Duration: {agent_result.duration:.2f}s")

    # Try to extract and parse JSON from response
    json_str = extract_json_from_response(agent_result.response)

    if json_str:
        try:
            data = json.loads(json_str)
            output = ReviewOutput.model_validate(data)
            logger.info(f"Successfully parsed ReviewOutput from agent {agent_result.agent_name}")
            logger.info(f"Findings: {len(output.findings)}, Severity: {output.severity}")
            return output
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse ReviewOutput JSON: {e}")
    else:
        logger.warning("No JSON found in agent response")

    # Fallback: Return default ReviewOutput for empty or invalid responses
    logger.info(
        f"Returning default ReviewOutput for agent {agent_result.agent_name} "
        "(no valid JSON extracted)"
    )

    return ReviewOutput(
        agent=agent_result.agent_name,
        summary=f"Review completed by {agent_result.agent_name} with note: No JSON output found in agent response",
        severity=Severity.MERGE,
        scope=Scope(
            relevant_files=context.changed_files,
            ignored_files=[],
            reasoning=f"Review based on changed files in {context.repo_root}",
        ),
        checks=[],
        skips=[],
        findings=[],
        merge_gate=MergeGate(
            decision=MergeDecision.APPROVE,
            must_fix=[],
            should_fix=[],
            notes_for_coding_agent=[
                f"Review completed by {agent_result.agent_name} "
                "but no structured findings were returned. "
                "Manual review recommended."
            ],
        ),
    )
