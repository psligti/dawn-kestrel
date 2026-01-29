"""OpenCode Python - Session Compaction"""
from __future__ import annotations
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


OUTPUT_TOKEN_MAX = 32_000
PRUNE_MINIMUM = 20_000
PRUNE_PROTECT = 40_000
PRUNE_PROTECTED_TOOLS = ["skill"]


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
    config = {
        "compaction": {"auto": True}  # TODO: Load from config
    }
    
    if config.get("compaction", {}).get("auto") is False:
        return False
    
    context = model.get("limit", {}).get("context", 0)
    if context == 0:
        return False
    
    count = tokens.get("input", 0) + tokens.get("cache_read", 0) + tokens.get("output", 0)
    output = min(
        model.get("limit", {}).get("output", 0),
        OUTPUT_TOKEN_MAX
    )
    usable = model.get("limit", {}).get("input", 0) or context - output
    
    return count > usable


async def prune(session_id: str) -> int:
    """
    Prune old tool outputs to reduce session size
    
    Args:
        session_id: Session ID to prune
    
    Returns:
        Number of tokens pruned
    """
    config = {
        "compaction": {"prune": True}  # TODO: Load from config
    }
    
    if config.get("compaction", {}).get("prune") is False:
        return 0
    
    # TODO: Load messages from storage
    msgs = []  # await SessionStorage.list_messages(session_id)
    total = 0
    pruned = 0
    to_prune = []
    turns = 0
    
    # Go backwards, skip last 2 turns, stop at summary
    for msg_index in range(len(msgs) - 1, -1, -1):
        msg = msgs[msg_index]
        if msg.get("role") == "user":
            turns += 1
        if turns < 2:
            continue  # Always keep last 2 turns
        if msg.get("role") == "assistant" and msg.get("summary"):
            break  # Stop at compaction
        
        # Find completed tool calls
        for part_index in range(len(msg.get("parts", [])) - 1, -1, -1):
            part = msg["parts"][part_index]
            if part.get("type") == "tool" and part.get("state", {}).get("status") == "completed":
                if part.get("tool") in PRUNE_PROTECTED_TOOLS:
                    continue  # Never prune certain tools
                
                time_compacted = part.get("state", {}).get("time_compacted")
                if time_compacted:
                    break  # Already compacted

                # Estimate tokens (simple char/4 heuristic)
                output = part.get("state", {}).get("output", "")
                estimate = len(output) // 4
                
                total += estimate
                
                if total > PRUNE_PROTECT:
                    pruned += estimate
                    to_prune.append(part)
    
    # Mark as compacted
    if pruned > PRUNE_MINIMUM:
        for part in to_prune:
            part["state"]["time_compacted"] = _now()
            # TODO: await SessionStorage.update_part(part)
    
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
    
    # Get model (would be from agent config)
    model = user_message.get("model", {})
    
    # Create compaction prompt
    default_prompt = (
        "Provide a detailed prompt for continuing our conversation above. "
        "Focus on information that would be helpful for continuing the conversation, including: "
        "what we did, what we're doing, which files we're working on, "
        "and what we're going to do next considering new session will not have access to our conversation."
    )
    
    # Build messages for LLM
    # TODO: Convert messages to LLM format
    context_messages = []
    for msg in messages:
        if msg.get("role") == "user":
            context_messages.append({
                "role": "user",
                "content": msg.get("parts", [{}])[0].get("text", "")
            })
        elif msg.get("role") == "assistant":
            parts_text = ""
            for part in msg.get("parts", []):
                if part.get("type") == "text":
                    parts_text += part.get("text", "")
            context_messages.append({
                "role": "assistant",
                "content": parts_text
            })
    
    # Add compaction prompt
    context_messages.append({
        "role": "user",
        "content": default_prompt,
    })
    
    # Call LLM (placeholder - will integrate with actual streaming)
    # TODO: Use LLM service to generate summary
    result = "continue"
    
    # If auto mode, optionally add "Continue" synthetic message
    if result == "continue" and auto:
        # TODO: Add synthetic message
        pass
    
    # Create assistant message with summary
    # TODO: await SessionStorage.create_message()
    
    return result


def _now() -> int:
    """Get current timestamp in milliseconds"""
    import time
    return int(time.time() * 1000)
