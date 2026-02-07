"""Utility functions for parsing and cleaning JSON from LLM responses."""
from __future__ import annotations

import re


def strip_json_code_blocks(text: str) -> str:
    """Extract JSON content from markdown code blocks.

    LLMs often wrap JSON responses in markdown code blocks like:
    ```json
    {"key": "value"}
    ```

    This function extracts the JSON content from such blocks.

    Args:
        text: Raw LLM response text, possibly containing markdown code blocks

    Returns:
        Cleaned JSON string. If no code blocks are found, returns original text.
    """
    if not text or not text.strip():
        return ""

    # Pattern to match markdown code blocks: ```json...``` or ```...```
    # Matches content between the opening ``` and closing ```
    code_block_pattern = r"```(?:json|markdown)?\s*\n([\s\S]*?)\n```"

    matches = re.findall(code_block_pattern, text, re.IGNORECASE)

    if matches:
        # Return content from the first code block found
        return matches[0].strip()

    # No code blocks found, return original text
    return text.strip()


def strip_any_code_blocks(text: str) -> str:
    """Extract content from any markdown code block.

    Like strip_json_code_blocks, but more aggressive - extracts content
    from ANY code block regardless of language marker.

    Args:
        text: Raw LLM response text, possibly containing markdown code blocks

    Returns:
        Cleaned content string. If no code blocks are found, returns original text.
    """
    if not text or not text.strip():
        return text

    # Pattern to match any code block: ```lang...``` or ```...```
    code_block_pattern = r"```\w*\s*\n([\s\S]*?)\n```"

    matches = re.findall(code_block_pattern, text)

    if matches:
        # Return content from the first code block found
        return matches[0].strip()

    # No code blocks found, return original text
    return text.strip()
