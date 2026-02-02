#!/usr/bin/env python3
"""Test API endpoint directly."""

import asyncio
from datetime import datetime
from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.core.services.session_service import DefaultSessionService
from opencode_python.storage.store import SessionStorage
from opencode_python.interfaces.io import QuietIOHandler
from pydantic import BaseModel

class CreateSessionRequest(BaseModel):
    title: str
    version: str = "1.0.0"

async def test():
    try:
        # Test SDK
        client = OpenCodeAsyncClient()
        session = await client.create_session('Test Session')
        print(f'SDK Session: {session}')
        print(f'ID: {session.id}')
        print(f'Title: {session.title}')
        print(f'Version: {session.version}')
        print(f'Time Created: {session.time_created}')
        print(f'Time Updated: {session.time_updated}')

        # Test session response
        response = {
            "id": session.id,
            "title": session.title,
            "version": "1.0.0",
            "created_at": datetime.fromtimestamp(session.time_created).isoformat(),
            "updated_at": datetime.fromtimestamp(session.time_updated).isoformat(),
        }
        print(f'Response: {response}')
        print(f'Response type: {type(response)}')
        print(f'Success!')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test())
