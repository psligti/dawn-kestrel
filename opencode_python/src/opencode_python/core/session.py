"""OpenCode Python - Core Session Management"""
from __future__ import annotations
from typing import Optional, List, Literal
from pathlib import Path
from datetime import datetime
import uuid
import logging

from opencode_python.storage.store import SessionStorage
from opencode_python.core.event_bus import bus, Events
from opencode_python.core.models import Session, Message, MessageSummary, SessionShare, SessionRevert


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
        created = await self.storage.create_session(session.model_dump(mode="json"))
        
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
        **kwargs,
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
        updated = await self.storage.update_session(session.model_dump(mode="json"))
        
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
        **kwargs,
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
        await self.storage.create_message(session_id, message.model_dump(mode="json"))
        
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
