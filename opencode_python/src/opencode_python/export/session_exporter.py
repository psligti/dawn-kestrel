"""OpenCode Python - Session Exporters"""
from __future__ import annotations
from typing import Literal, Optional, Any
from datetime import datetime
import json
import re
from abc import ABC, abstractmethod

from opencode_python.core.models import Session, Message
from opencode_python.storage.session_meta import SessionMeta


class BaseExporter(ABC):
    """Base class for session exporters"""

    def __init__(self, redact_secrets: bool = True):
        self.redact_secrets = redact_secrets
        self.secret_patterns = ["api_key", "token", "password", "secret"]

    @abstractmethod
    async def export(
        self,
        session: Session,
        meta: Optional[SessionMeta] = None,
        messages: list[Message] = [],
    ) -> str:
        pass

    def _redact_text(self, text: str) -> str:
        if not self.redact_secrets:
            return text
        for pattern in self.secret_patterns:
            text = re.sub(
                rf'{pattern}["\']?\s*[:=]\s*[^\s,}}]+',
                f'{pattern}=***REDACTED***',
                text,
                flags=re.IGNORECASE
            )
        return text


class MarkdownExporter(BaseExporter):
    """Export session to Markdown format"""

    async def export(
        self,
        session: Session,
        meta: Optional[SessionMeta] = None,
        messages: list[Message] = [],
    ) -> str:
        """Export session to Markdown

        Args:
            session: Session to export
            meta: Session metadata
            messages: List of messages

        Returns:
            Markdown content as string
        """
        lines = []

        lines.append(f"# Session: {session.title}")
        lines.append(f"**ID:** {session.id}")
        lines.append(f"**Created:** {datetime.fromtimestamp(session.time_created).isoformat()}")
        lines.append(f"**Updated:** {datetime.fromtimestamp(session.time_updated).isoformat()}")

        if meta:
            if meta.repo_path:
                lines.append(f"\n**Repository:** {meta.repo_path}")
            if meta.objective:
                lines.append(f"**Objective:** {meta.objective}")
            if meta.constraints:
                lines.append(f"**Constraints:** {meta.constraints}")

        lines.append("\n---\n## Messages\n")

        for msg in messages:
            lines.append(f"\n### {msg.role.upper()} - Message {msg.id[:8]}")

            if msg.text:
                lines.append(f"\n{self._redact_text(msg.text)}")

            for part in msg.parts:
                if part.part_type == "tool":
                    lines.append(f"\n**Tool Call:** {part.tool}")
                    if part.state.error:
                        lines.append(f"**Error:** {part.state.error}")
                    if part.state.output:
                        lines.append(f"**Output:**\n```\n{self._redact_text(str(part.state.output))}\n```")

        return "\n".join(lines)


class JSONExporter(BaseExporter):
    """Export session to JSON format"""

    async def export(
        self,
        session: Session,
        meta: Optional[SessionMeta] = None,
        messages: list[Message] = [],
    ) -> str:
        """Export session to JSON

        Args:
            session: Session to export
            meta: Session metadata
            messages: List of messages

        Returns:
            JSON content as string
        """
        export_data: dict[str, Any] = {
            "session": session.model_dump(mode="json"),
            "meta": meta.model_dump(mode="json") if meta else None,
            "messages": [],
        }

        for msg in messages:
            msg_data = msg.model_dump(mode="json", exclude_none=True)

            if self.redact_secrets and msg.text:
                msg_data["text"] = self._redact_text(msg.text)

            if isinstance(export_data["messages"], list):
                export_data["messages"].append(msg_data)

        return json.dumps(export_data, indent=2, ensure_ascii=False)


async def export_session(
    session: Session,
    meta: Optional[SessionMeta] = None,
    messages: list[Message] = [],
    format: Literal["markdown", "json"] = "markdown",
    redact_secrets: bool = True,
) -> str:
    """Export a session to the specified format

    Args:
        session: Session to export
        meta: Session metadata
        messages: List of messages
        format: Export format ("markdown" or "json")
        redact_secrets: Whether to redact sensitive information

    Returns:
        Exported content as string
    """
    if format == "json":
        exporter: BaseExporter = JSONExporter(redact_secrets=redact_secrets)
    else:
        exporter = MarkdownExporter(redact_secrets=redact_secrets)

    return await exporter.export(session, meta, messages)
