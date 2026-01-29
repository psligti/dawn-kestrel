"""OpenCode Python - Core Session Management"""
from __future__ import annotations
from typing import Optional, List, Literal, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

from opencode_python.storage.store import SessionStorage
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
        
        # Persist
        created = await self.storage.create_session(session)
        
        logger.info(f"Created session: {session_id} ({title})")
        
        # Emit event
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
        
        # Persist
        updated = await self.storage.update_session(session)
        
        # Emit event
        await bus.publish(Events.SESSION_UPDATED, {"session": session.model_dump()})
        
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Delete from storage
        deleted = await self.storage.delete_session(session_id, session.project_id)
        
        # Emit event
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

        # Delete from storage
        deleted = await self.storage.remove(["message", session_id, message_id])

        # Emit event
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

        # Validate required fields
        if not session_dict.get("id") or not session_dict.get("title"):
            raise ValueError("Session data missing required fields: id, title")

        # Create or update session
        existing = await self.storage.get_session(session_dict["id"])
        project = project_id or self.project_dir.name

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
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower().strip()
        # Replace multiple spaces/hyphens with single hyphen
        slug = re.sub(r'\s+', '-', slug)
        # Remove special characters except alphanumeric, hyphens, and underscores
        slug = re.sub(r'[^a-z0-9_-]', '', slug)
        # Limit length
        slug = slug[:100]
        return slug
