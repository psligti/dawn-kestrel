"""OpenCode Python - Core Session Management"""
from __future__ import annotations
from typing import Optional, List, Literal, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

from opencode_python.storage.store import SessionStorage
from opencode_python.storage.session_meta import SessionMeta, SessionMetaStorage
from opencode_python.core.event_bus import bus, Events
from opencode_python.core.models import (
    Session,
    Message,
    MessageSummary,
    Part,
)


logger = logging.getLogger(__name__)


class SessionManager:
    """Session lifecycle management"""

    def __init__(
        self,
        storage: SessionStorage,
        project_dir: Path,
    ):
        self.storage = storage
        self.project_dir = project_dir

    @property
    def directory(self) -> str:
        """Get the project directory path"""
        return str(self.project_dir)

    async def create(
        self,
        title: str,
        parent_id: Optional[str] = None,
        version: str = "1.0.0",
        summary: Optional["MessageSummary"] = None,
    ) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        # Generate slug from title
        slug = title.lower().replace(" ", "-")
        
        session = Session(
            id=session_id,
            slug=slug,
            project_id=self.project_dir.name,
            directory=str(self.project_dir),
            parent_id=parent_id,
            title=title,
            version=version,
            summary=summary,
        )

        await self.storage.create_session(session)

        logger.info(f"Created session: {session_id} ({title})")

        await bus.publish(Events.SESSION_CREATED, {"session": session.model_dump()})

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        return await self.storage.get_session(session_id)

    async def update_session(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> Session:
        """Update session metadata"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.time_updated = datetime.now().timestamp()

        await self.storage.update_session(session)

        await bus.publish(Events.SESSION_UPDATED, {"session": session.model_dump()})

        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session = await self.get_session(session_id)
        if not session:
            return False

        await self.storage.delete_session(session_id, session.project_id)

        await bus.publish(Events.SESSION_DELETED, {"session_id": session_id})

        logger.info(f"Deleted session: {session_id}")

        return True

    async def list_sessions(self) -> List[Session]:
        """List all sessions for a project"""
        sessions = await self.storage.list_sessions(self.project_dir.name)
        return sessions

    async def create_message(
        self,
        session_id: str,
        role: Literal["user", "assistant", "system"],
        text: str = "",
        **kwargs: Any,
    ) -> None:
        """Create a message in a session"""
        # Create message
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            time={"created": datetime.now().timestamp()},
            text=text,
            **kwargs,
        )
        
        # Persist message
        from opencode_python.storage.store import MessageStorage
        message_storage = MessageStorage(self.storage.base_dir)
        await message_storage.create_message(session_id, message)
        
        # Emit event
        await bus.publish(Events.MESSAGE_CREATED, {"message": message.model_dump()})
        
        logger.debug(f"Created message {message.id} in session {session_id}")
    
    async def create_messages(self, session_id: str, messages: List["Message"]) -> None:
        """Create multiple messages in a session (preserves original IDs and timestamps)"""
        from opencode_python.storage.store import MessageStorage

        message_storage = MessageStorage(self.storage.base_dir)

        for message in messages:
            await message_storage.create_message(session_id, message)

        logger.info(f"Created {len(messages)} messages in session {session_id}")

    async def list_messages(self, session_id: str) -> List["Message"]:
        """List all messages for a session"""
        from opencode_python.storage.store import MessageStorage

        message_storage = MessageStorage(self.storage.base_dir)

        messages_data = await message_storage.list_messages(session_id)

        from opencode_python.core.models import Message

        messages = [Message(**msg) for msg in messages_data]

        return messages

    async def list_all(self) -> List[Session]:
        """List all sessions for current project (alias for list_sessions)"""
        return await self.list_sessions()

    async def get_messages(self, session_id: str) -> List["Message"]:
        """Get all messages for a session (alias for list_messages)"""
        return await self.list_messages(session_id)

    async def delete_message(self, session_id: str, message_id: str) -> bool:
        """Delete a message from a session"""
        from opencode_python.storage.store import MessageStorage

        message_storage = MessageStorage(self.storage.base_dir)

        # Check if message exists
        message = await message_storage.get_message(session_id, message_id)
        if not message:
            return False

        await self.storage.remove(["message", session_id, message_id])

        await bus.publish(Events.MESSAGE_DELETED, {
            "session_id": session_id,
            "message_id": message_id
        })

        logger.info(f"Deleted message {message_id} from session {session_id}")

        return True

    async def add_message(self, message: "Message") -> str:
        """Add a message to a session"""
        from opencode_python.storage.store import MessageStorage

        message_storage = MessageStorage(self.storage.base_dir)

        # Persist message
        await message_storage.create_message(message.session_id, message)

        # Emit event
        await bus.publish(Events.MESSAGE_CREATED, {"message": message.model_dump()})

        logger.debug(f"Added message {message.id} to session {message.session_id}")

        return message.id

    async def add_part(self, part: Part) -> str:
        """Add a part to a message"""
        from opencode_python.storage.store import PartStorage

        part_storage = PartStorage(self.storage.base_dir)

        # Persist part
        await part_storage.create_part(part.message_id, part)

        # Emit event
        await bus.publish(Events.MESSAGE_PART_UPDATED, {
            "message_id": part.message_id,
            "part_id": part.id
        })

        logger.debug(f"Added part {part.id} to message {part.message_id}")

        return part.id

    async def get_export_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for export (session + all messages + parts)"""
        # Get session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Get all messages with parts
        messages = await self.list_messages(session_id)

        # Build export data
        export_data = {
            "session": session.model_dump(mode="json"),
            "messages": [msg.model_dump(mode="json", exclude_none=True) for msg in messages]
        }

        logger.info(f"Exported session {session_id} with {len(messages)} messages")

        return export_data

    async def import_data(self, session_data: Dict[str, Any], project_id: Optional[str] = None) -> Session:
        """Import session data (session + messages)"""

        session_dict = session_data.get("session", {})
        messages_data = session_data.get("messages", [])

        if not session_dict.get("id") or not session_dict.get("title"):
            raise ValueError("Session data missing required fields: id, title")

        existing = await self.storage.get_session(session_dict["id"])
        _project_id = project_id or self.project_dir.name

        if existing:
            # Update existing session
            session = await self.update_session(
                session_dict["id"],
                title=session_dict.get("title"),
                summary=session_dict.get("summary"),
            )
        else:
            # Create new session
            session = await self.create(
                title=session_dict.get("title", "Imported Session"),
                parent_id=session_dict.get("parent_id"),
                version=session_dict.get("version", "1.0.0"),
                summary=session_dict.get("summary"),
            )

        # Import messages
        from opencode_python.core.models import Message
        messages = []
        for msg_data in messages_data:
            message = Message(**msg_data)
            message.session_id = session.id
            messages.append(message)

        await self.create_messages(session.id, messages)

        logger.info(f"Imported session {session.id} with {len(messages)} messages")

        return session

    async def get_todos(self, session_id: str) -> List[Dict[str, Any]]:
        """Get todos associated with a session"""
        # TODO: Implement todo storage when todo system is complete
        return []

    async def update_todos(self, session_id: str, todos: List[Dict[str, Any]]) -> None:
        """Update todos for a session"""
        # TODO: Implement todo storage when todo system is complete
        pass

    async def get_user_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get user questions from a session"""
        # TODO: Implement question tracking when question system is complete
        return []

    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-friendly slug from title"""
        import re
        slug = title.lower().strip()
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'[^a-z0-9_-]', '', slug)
        slug = slug[:100]
        return slug

    def _get_meta_storage(self) -> SessionMetaStorage:
        """Get session meta storage instance"""
        return SessionMetaStorage(self.storage.base_dir)

    async def validate_repo_path(self, repo_path: str) -> bool:
        """Validate that a repository path exists and is a directory"""
        path = Path(repo_path)
        return path.exists() and path.is_dir()

    async def create_with_context(
        self,
        title: str,
        repo_path: str,
        objective: Optional[str] = None,
        constraints: Optional[str] = None,
        parent_id: Optional[str] = None,
        version: str = "1.0.0",
    ) -> Session:
        """Create a new session with repository context

        Args:
            title: Session title
            repo_path: Path to git repository
            objective: Session objective/goal
            constraints: Session constraints
            parent_id: Parent session ID
            version: Session version

        Returns:
            Created session

        Raises:
            ValueError: If repo_path does not exist
        """
        if not await self.validate_repo_path(repo_path):
            raise ValueError(f"Invalid repository path: {repo_path}")

        session = await self.create(
            title=title,
            parent_id=parent_id,
            version=version,
        )

        meta = SessionMeta(
            repo_path=repo_path,
            objective=objective,
            constraints=constraints,
        )

        meta_storage = self._get_meta_storage()
        await meta_storage.save_meta(session.id, meta)

        logger.info(f"Created session with context: {session.id} (repo: {repo_path})")

        return session

    async def get_session_meta(self, session_id: str) -> Optional[SessionMeta]:
        """Get session metadata"""
        meta_storage = self._get_meta_storage()
        return await meta_storage.get_meta(session_id)

    async def update_session_meta(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> SessionMeta:
        """Update session metadata"""
        meta_storage = self._get_meta_storage()
        meta = await meta_storage.update_meta(session_id, **kwargs)

        await bus.publish(Events.SESSION_AUTOSAVE, {
            "session_id": session_id,
            "meta": meta.model_dump()
        })

        return meta

    async def resume_session(self, session_id: str) -> tuple[Session, Optional[SessionMeta]]:
        """Resume a session exactly as it was saved

        Args:
            session_id: Session ID to resume

        Returns:
            Tuple of (session, session_meta)

        Raises:
            ValueError: If session not found
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        meta = await self.get_session_meta(session_id)

        await bus.publish(Events.SESSION_RESUMED, {
            "session_id": session_id,
            "session": session.model_dump(),
            "meta": meta.model_dump() if meta else None
        })

        logger.info(f"Resumed session: {session_id}")

        return session, meta

    async def autosave(self, session_id: str) -> None:
        """Trigger auto-save for a session (emit event only, data already persisted)"""
        await bus.publish(Events.SESSION_AUTOSAVE, {
            "session_id": session_id,
            "timestamp": datetime.now().timestamp()
        })

    async def export_session(
        self,
        session_id: str,
        format: Literal["markdown", "json"] = "markdown",
        redact_secrets: bool = True,
    ) -> str:
        """Export a session to the specified format

        Args:
            session_id: Session ID to export
            format: Export format ("markdown" or "json")
            redact_secrets: Whether to redact sensitive information

        Returns:
            Exported content as string
        """
        if format == "json":
            return await self._export_json(session_id)
        else:
            return await self._export_markdown(session_id, redact_secrets)

    async def _export_json(self, session_id: str) -> str:
        """Export session to JSON format"""
        import json

        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        meta = await self.get_session_meta(session_id)
        messages = await self.list_messages(session_id)

        export_data = {
            "session": session.model_dump(mode="json"),
            "meta": meta.model_dump(mode="json") if meta else None,
            "messages": [msg.model_dump(mode="json", exclude_none=True) for msg in messages],
        }

        result = json.dumps(export_data, indent=2, ensure_ascii=False)

        await bus.publish(Events.SESSION_EXPORT, {
            "session_id": session_id,
            "format": "json"
        })

        return result

    async def _export_markdown(self, session_id: str, redact_secrets: bool) -> str:
        """Export session to Markdown format with optional secret redaction"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        meta = await self.get_session_meta(session_id)
        messages = await self.list_messages(session_id)

        secret_patterns = ["api_key", "token", "password", "secret"]

        def redact_text(text: str) -> str:
            if not redact_secrets:
                return text
            import re
            for pattern in secret_patterns:
                text = re.sub(rf'{pattern}["\']?\s*[:=]\s*[^\s,}}]+', f'{pattern}=***REDACTED***', text, flags=re.IGNORECASE)
            return text

        lines = []
        lines.append(f"# Session: {session.title}")
        lines.append(f"**ID:** {session.id}")
        lines.append(f"**Created:** {datetime.fromtimestamp(session.time_updated).isoformat()}")

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
                lines.append(f"\n{redact_text(msg.text)}")

            for part in msg.parts:
                if part.part_type == "tool":
                    lines.append(f"\n**Tool Call:** {part.tool}")
                    if part.state.error:
                        lines.append(f"**Error:** {part.state.error}")
                    if part.state.output:
                        lines.append(f"**Output:**\n```\n{redact_text(str(part.state.output))}\n```")

        result = "\n".join(lines)

        await bus.publish(Events.SESSION_EXPORT, {
            "session_id": session_id,
            "format": "markdown"
        })

        return result
