"""Grader specification models for evaluation framework.

This module defines the GraderSpec model and well-known grader types
for the Dawn Kestrel evaluation framework. Grader specs are consumed
by ash-hawk (external evaluation harness) to configure how evaluations
are graded.
"""

from __future__ import annotations

from typing import Any

import pydantic as pd


# Well-known grader type constants (extensible, not enum)
GRADER_TYPE_DETERMINISTIC_TESTS = "deterministic_tests"
GRADER_TYPE_LLM_RUBRIC = "llm_rubric"
GRADER_TYPE_STATIC_ANALYSIS = "static_analysis"
GRADER_TYPE_STATE_CHECK = "state_check"
GRADER_TYPE_TOOL_CALLS = "tool_calls"
GRADER_TYPE_TRANSCRIPT = "transcript"


class GraderSpec(pd.BaseModel):
    """Specification for a grader configuration.

    Graders evaluate task outputs and determine success/failure.
    The type field determines which grader implementation to use,
    while config provides grader-specific parameters.

    Attributes:
        type: Grader implementation type (use well-known constants above,
            or custom string for extensible grader types).
        name: Human-readable name for this grader instance.
        config: Grader-specific configuration parameters.

    Example:
        >>> spec = GraderSpec(
        ...     type=GRADER_TYPE_LLM_RUBRIC,
        ...     name="code_quality_check",
        ...     config={"rubric": "Is the code well-structured?", "threshold": 0.8}
        ... )
        >>> spec.to_dict()
        {'type': 'llm_rubric', 'name': 'code_quality_check', 'config': {...}}
    """

    type: str
    name: str
    config: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all model fields.
        """
        return self.model_dump()
