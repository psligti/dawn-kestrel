"""OpenCode Python - Session Compaction"""
from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from dawn_kestrel.core.settings import settings


logger = logging.getLogger(__name__)


OUTPUT_TOKEN_MAX = 32_000
PRUNE_MINIMUM = 20_000
PRUNE_PROTECT = 40_000
PRUNE_PROTECTED_TOOLS = ["skill"]


def _now() -> int:
    import time
    return int(time.time())


async def is_overflow(
    tokens: Dict[str, int],
    model: Dict[str, Any]
) -> bool:
    """
    Check if session has exceeded usable context limit

    Args:
        tokens: Token counts (input, cache_read, output)
        model: Model configuration with limits

    Returns:
        True if compaction needed
    """
    config: Dict[str, Any] = getattr(settings, "compaction", {"auto": True})

    if not config.get("auto"):
        return False

    context = model.get("limit", {}).get("context", 0)
    if context == 0:
        return False

    count = tokens.get("input", 0) + tokens.get("cache_read", 0) + tokens.get("output", 0)
    output = min(
        model.get("limit", {}).get("output", 0),
        OUTPUT_TOKEN_MAX
    )
    usable = model.get("limit", {}).get("input", context) or (context - output)

    return count > usable


async def prune(session_id: str) -> int:
    """
    Prune old tool outputs to reduce session size

    Args:
        session_id: Session ID to prune

    Returns:
        Number of tokens pruned
    """
    config = getattr(settings, "compaction", {"prune": True})

    if not config.get("prune"):
        return 0

    # Load messages from storage
    from dawn_kestrel.storage.store import MessageStorage

    message_storage = MessageStorage(Path.cwd())
    msgs = []
    total = 0
    pruned = 0
    to_prune = []
    turns = 0

    for key in await message_storage.list([f"message/{session_id}"]):
        msg_data = await message_storage.read(key)
        if msg_data:
            msgs.append(msg_data)

    # Go backwards, skip last 2 turns, stop at summary
    for msg_index in range(len(msgs) - 1, -1, -1):
        msg = msgs[msg_index]
        if msg.get("role") == "user":
            turns += 1
        if turns < 2:
            continue

        if msg.get("role") == "assistant" and msg.get("summary"):
            break

        # Find completed tool calls
        for part in msg.get("parts", []):
            if part.get("part_type") == "tool" and part.get("state", {}).get("status") == "completed":
                if part.get("tool") in PRUNE_PROTECTED_TOOLS:
                    continue

                time_compacted = part.get("state", {}).get("time_compacted")
                if time_compacted:
                    break

                output = part.get("state", {}).get("output", "")
                if not output:
                    continue

                if part.get("tool") in PRUNE_PROTECTED_TOOLS:
                    continue

                estimate = len(output) // 4

                total += estimate

                if total > PRUNE_PROTECT:
                    pruned += estimate
                    to_prune.append(part)

    # Mark as compacted
    if pruned > PRUNE_MINIMUM:
        for part in to_prune:
            part["state"]["time_compacted"] = _now()

    return pruned


async def process(
    parent_id: str,
    messages: list,
    session_id: str,
    abort: Optional[Any] = None,
    auto: bool = False,
) -> str:
    """
    Process compaction by asking LLM to summarize conversation

    Args:
        parent_id: ID of last user message
        messages: List of messages to summarize
        session_id: Session ID
        abort: Abort signal
        auto: Auto-mode flag

    Returns:
        "continue" if conversation can continue
    """

    # Find parent user message
    user_message = None
    for msg in messages:
        if msg.get("id") == parent_id and msg.get("role") == "user":
            user_message = msg
            break

    if not user_message:
        logger.error(f"Parent user message not found: {parent_id}")
        return "error"

    model_info = {}

    # Build context for LLM
    context_messages = []
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("parts", [{}])[0].get("text", "")
            context_messages.append({"role": "user", "content": content})
        elif msg.get("role") == "assistant":
            parts_text = ""
            for part in msg.get("parts", []):
                if part.get("part_type") == "text":
                    parts_text += part.get("text", "")
            context_messages.append({"role": "assistant", "content": parts_text})

    # Add default prompt
    from dawn_kestrel.core.models import CompactionPart
    compaction_part_id = f"{session_id}_compaction"

    prompt_parts = context_messages.copy()
    prompt_parts.append({
        "role": "user",
        "content": "Summarize our conversation above. Focus on information that would be helpful for continuing: what we did, what we're doing, which files we're working on, and what we're going to do next.",
        "parts": [
            CompactionPart(
                id=compaction_part_id,
                session_id=session_id,
                message_id=compaction_part_id,
                part_type="compaction",
                auto=auto
            )
        ]
    })
    prompt_parts.append({
        "role": "system",
        "content": "You are a helpful AI assistant. Summarize the conversation above in a way that allows continuing without losing important context."
    })

    # For now, return "continue" without LLM integration
    logger.info(f"Compaction would process {len(messages)} messages")

    return "continue"
