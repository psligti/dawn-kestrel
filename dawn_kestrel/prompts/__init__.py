"""Prompt templates package for Dawn Kestrel.

This package contains prompt templates for various LLM interactions,
organized by category. The FSM prompts are used by the workflow FSM
for structured multi-phase workflows.

Example usage:
    from dawn_kestrel.prompts.loader import load_prompt

    # Load an FSM prompt template
    prompt = load_prompt("fsm/intake")

    # Format with runtime variables
    formatted = prompt.format(
        user_message="Add authentication",
        schema=get_intake_output_schema()
    )
"""

from dawn_kestrel.prompts.loader import (
    clear_cache,
    get_prompt_path,
    list_prompts,
    load_prompt,
)

__all__ = [
    "load_prompt",
    "clear_cache",
    "get_prompt_path",
    "list_prompts",
]
