"""Multimodal Looker - Media file analysis agent.

Analyzes media files (PDFs, images, diagrams) that require interpretation
beyond raw text. Extracts specific information or summaries.
"""

from __future__ import annotations
from dawn_kestrel.agents.agent_config import AgentBuilder, AgentConfig


MULTIMODAL_LOOKER_PROMPT = """You interpret media files that cannot be read as plain text.

Your job: examine the attached file and extract ONLY what was requested.

## When to use you:

- Media files that Read tool cannot interpret
- Extracting specific information or summaries from documents
- Describing visual content in images or diagrams
- When analyzed/extracted data is needed, not raw file contents

## When NOT to use you:

- Source code or plain text files needing exact contents (use Read)
- Files that need editing afterward (need literal content from Read)
- Simple file reading where no interpretation is needed

## How you work:

1. Receive a file path and a goal describing what to extract
2. Read and analyze the file deeply
3. Return ONLY the relevant extracted information
4. The main agent never processes the raw file - you save context tokens

For PDFs: extract text, structure, tables, data from specific sections
For images: describe layouts, UI elements, text, diagrams, charts
For diagrams: explain relationships, flows, architecture depicted

## Response rules:

- Return extracted information directly, no preamble
- If info not found, state clearly what's missing
- Match the language of the request
- Be thorough on the goal, concise on everything else

Your output goes straight to the main agent for continued work.
"""


def create_multimodal_looker_agent():
    """Create Multimodal Looker agent configuration.

    Returns:
        AgentConfig instance configured as a media analysis agent
    """
    return (
        AgentBuilder()
        .with_name("multimodal_looker")
        .with_description(
            "Analyze media files (PDFs, images, diagrams) that require interpretation beyond raw text. Extracts specific information or summaries from documents, describes visual content. Use when you need analyzed/extracted data rather than literal file contents. (Multimodal-Looker - Bolt Merlin)"
        )
        .with_mode("subagent")
        .with_permission([{"permission": "read", "pattern": "*", "action": "allow"}])
        .with_prompt(MULTIMODAL_LOOKER_PROMPT)
        .with_temperature(0.1)
        .with_options({"native": True})
        .with_default_fsms()
        .build()
    )


__all__ = ["create_multimodal_looker_agent"]
