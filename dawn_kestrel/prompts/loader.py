"""Prompt loader utility for loading prompt templates from markdown files.

This module provides a simple interface for loading prompt templates from
the prompts/ directory with caching support for repeated loads.

Usage:
    from dawn_kestrel.prompts.loader import load_prompt

    # Load a prompt template
    prompt = load_prompt("fsm/intake")

    # Format with variables
    formatted = prompt.format(user_message="Hello", schema=schema_str)
"""

from pathlib import Path

_prompt_cache: dict[str, str] = {}
_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by name.

    Loads a markdown file from the prompts directory and extracts the
    prompt template section. Supports caching for repeated loads.

    Args:
        name: Prompt name in format "category/prompt_name" (e.g., "fsm/intake")
              or just "prompt_name" for prompts in the root directory.

    Returns:
        The prompt template string (content within the Prompt Template section).

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError: If the prompt file doesn't contain a valid template section.

    Example:
        >>> prompt = load_prompt("fsm/intake")
        >>> formatted = prompt.format(user_message="Hello", schema=schema)
    """
    if name in _prompt_cache:
        return _prompt_cache[name]

    prompt_path = _PROMPTS_DIR / f"{name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. Expected prompt at: {name}.md"
        )

    content = prompt_path.read_text(encoding="utf-8")
    template = _extract_template(content)
    _prompt_cache[name] = template
    return template


def _extract_template(content: str) -> str:
    """Extract the prompt template from markdown content.

    Looks for the "## Prompt Template" section and extracts the content
    within the code block that follows it.

    Args:
        content: The full markdown file content.

    Returns:
        The extracted template string.

    Raises:
        ValueError: If no valid template section is found.
    """
    template_marker = "## Prompt Template"
    marker_idx = content.find(template_marker)

    if marker_idx == -1:
        return content.strip()

    after_marker = content[marker_idx + len(template_marker) :]
    code_block_start = after_marker.find("```")
    if code_block_start == -1:
        raise ValueError(
            "Prompt file has '## Prompt Template' section but no code block. "
            "Expected a ``` code block containing the template."
        )

    after_code_start = after_marker[code_block_start + 3 :]
    newline_after_start = after_code_start.find("\n")
    if newline_after_start != -1:
        template_start = newline_after_start + 1
    else:
        template_start = 0

    remaining = after_code_start[template_start:]
    code_block_end = remaining.find("```")

    if code_block_end == -1:
        raise ValueError(
            "Prompt file has unclosed code block in '## Prompt Template' section. "
            "Expected closing ```."
        )

    return remaining[:code_block_end].strip()


def clear_cache() -> None:
    """Clear the prompt cache.

    Useful for testing or when prompt files have been updated on disk.
    """
    global _prompt_cache
    _prompt_cache = {}


def get_prompt_path(name: str) -> Path:
    """Get the file path for a prompt by name.

    Args:
        name: Prompt name in format "category/prompt_name".

    Returns:
        Path to the prompt file.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    prompt_path = _PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path


def list_prompts(category: str = "") -> list[str]:
    """List available prompts, optionally filtered by category.

    Args:
        category: Optional category to filter by (e.g., "fsm").
                  If empty, lists all prompts.

    Returns:
        List of prompt names (without .md extension).

    Example:
        >>> list_prompts("fsm")
        ['fsm/intake', 'fsm/plan', 'fsm/act', 'fsm/synthesize', 'fsm/check']
    """
    prompts: list[str] = []

    if category:
        search_dir = _PROMPTS_DIR / category
        if not search_dir.exists():
            return []
        prefix = f"{category}/"
    else:
        search_dir = _PROMPTS_DIR
        prefix = ""

    for md_file in search_dir.glob("**/*.md"):
        rel_path = md_file.relative_to(_PROMPTS_DIR)
        prompt_name = str(rel_path.with_suffix(""))
        if prefix and not prompt_name.startswith(prefix):
            continue
        prompts.append(prompt_name)

    return sorted(prompts)
