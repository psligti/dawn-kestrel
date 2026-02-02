#!/usr/bin/env python3
"""Test storage directly."""

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.storage.store import SessionStorage
from pathlib import Path
import asyncio
import tempfile
import shutil

async def test_storage():
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")

        # Create a client with this storage directory
        client1 = OpenCodeAsyncClient()
        print(f"Client 1 storage_dir: {client1.config.storage_path}")
        print(f"Client 1 project_dir: {client1.project_dir}")

        # Create a session
        session = await client1.create_session('Test Session 1')
        print(f"Created session: {session.id}")
        print(f"Session location: {session.directory}")

        # Create another client with the same storage directory
        client2 = OpenCodeAsyncClient()
        print(f"Client 2 storage_dir: {client2.config.storage_path}")
        print(f"Client 2 project_dir: {client2.project_dir}")

        # Try to get the session with client2
        retrieved = await client2.get_session(session.id)
        print(f"Retrieved session with client2: {retrieved}")
        if retrieved:
            print(f"Retrieved session title: {retrieved.title}")
        else:
            print("FAILED: Session not found with client2")

        # List all sessions with client2
        all_sessions = await client2.list_sessions()
        print(f"All sessions with client2: {len(all_sessions)}")
        for s in all_sessions:
            print(f"  - {s.id}: {s.title} (project_id: {s.project_id})")

if __name__ == "__main__":
    asyncio.run(test_storage())
