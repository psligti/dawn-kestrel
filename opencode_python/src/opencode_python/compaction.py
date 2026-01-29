"""
Session compaction for managing token overflow and context summarization.

Automatically detects when token limit is exceeded, creates summary
messages with compaction agent, and prunes old tool outputs.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal

from .core.settings import settings
from .core.event_bus import bus, Events
from .core.models import Session, Message as MessageModel
from .agents.builtin import build as AgentCompaction
from .providers import get_available_models


logger = logging.getLogger(__name__)


class SessionCompactor:
    def __init__(self, session_id: str, model_limit: int):
        self.session_id = session_id
        self.model_limit = model_limit
        self.last_compaction_tokens = 0
        self.total_compactions = 0
    
    async def check_overflow(self, total_tokens: int, messages: list) -> bool:
        """Check if session should be compacted"""
        if total_tokens >= self.model_limit:
            logger.info(f"Token overflow detected: {total_tokens}/{self.model_limit}")
            return True
        return False
    
    async def compact(self, session: Session, messages: list[MessageModel]) -> Optional[str]:
        """Compact session by creating summary and pruning old messages"""
        from .core.session import SessionManager
        
        session_mgr = SessionManager()
        
        if not await self.check_overflow(len(messages), messages):
            logger.info("No overflow detected, skipping compaction")
            return None
        
        logger.info(f"Starting session compaction ({len(messages)} messages)")
        
        compacted_messages = []
        tokens_to_keep = int(self.model_limit * 0.6)
        tokens_pruned = 0
        
        for idx, msg in enumerate(messages):
            if idx < len(messages) - 10:
                tokens_to_keep += self._count_message_tokens(msg)
            else:
                tokens_to_keep += self._count_message_tokens(msg)
                tokens_pruned += self._count_message_tokens(msg)
        
        logger.info(f"Keeping {tokens_to_keep}/{self.last_compaction_tokens} tokens, pruned {tokens_pruned}")
        self.last_compaction_tokens = tokens_to_keep
        
        summary = self._generate_summary(messages)
        
        compaction_part = session_mgr.create_part(
            session_id=self.session_id,
            message_id=messages[0].id if messages else "",
            part_type="compaction",
            text=f"Session compacted. {tokens_pruned} tokens pruned, {len(messages) - 10} messages removed. Summary: {summary[:200]}...",
            metadata={
                "compaction_id": f"compaction_{self.total_compactions + 1}",
                "tokens_kept": tokens_to_keep,
                "tokens_pruned": tokens_pruned,
                "message_count": len(messages),
                "tokens_before": len(messages) - len(messages) + tokens_pruned
                "tokens_after": len(messages)
            }
        )
        
        await session_mgr.add_part(compaction_part)
        
        summary_message = session_mgr.create_message(
            session_id=self.session_id,
            role="assistant",
            role="system",
            parts=[{
                "id": f"{self.session_id}_summary",
                "session_id": self.session_id,
                "message_id": messages[0].id if messages else "",
                "part_type": "compaction"
                "text": f"Session compaction complete. Summary: {summary}"
            }]
        )
        
        summary_id = await session_mgr.add_message(summary_message)
        
        logger.info(f"Created summary message: {summary_id}")
        
        self.total_compactions += 1
        
        return summary_id
    
    def _count_message_tokens(self, msg: MessageModel) -> int:
        """Count total tokens in message"""
        total = 0
        
        for part in msg.get("parts", []):
            part_type = part.get("part_type", "")
            
            if part_type in ["text", "reasoning"]:
                total += len(part.get("text", ""))
            elif part_type in ["tool", "snapshot", "patch", "agent", "subtask"]:
                total += 50
            elif part_type == "file":
                total += 100
            elif part_type == "retry":
                total += 25
        
        return total
    
    def _generate_summary(self, messages: list[MessageModel]) -> str:
        """Generate session summary for compaction"""
        if not messages:
            return "No messages to summarize"
        
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg
                break
        
        if not last_user_msg:
            return "No user message found"
        
        user_content = last_user_msg.get("parts", [])[-1].get("text", "") if last_user_msg.get("parts") else ""
        
        tool_calls = []
        for msg in messages:
            for part in msg.get("parts", []):
                if part.get("part_type") == "tool":
                    tool_calls.append(f"  {part.get('tool', '')}")
        
        tool_summary = f"Executed {len(tool_calls)} tool calls: {', '.join(tool_calls[:10])}"
        
        file_changes = []
        for msg in messages:
            for part in msg.get("parts", []):
                if part.get("part_type") == "patch":
                    files = part.get("files", [])
                    file_changes.extend(files)
        
        changes_summary = f"Modified {len(file_changes)} files: {', '.join(file_changes[:10])}"
        
        summary_parts = [
            f"Current state: {user_content[:200]}",
            f"{tool_summary}",
            f"{changes_summary}",
            f"Recent activity summary"
        ]
        
        full_summary = "\n".join(summary_parts)
        
        return full_summary[:500]
