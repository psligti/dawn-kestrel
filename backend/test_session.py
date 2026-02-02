#!/usr/bin/env python3
"""Test SDK create_session directly."""

from opencode_python.sdk import OpenCodeAsyncClient
import asyncio

async def test():
    client = OpenCodeAsyncClient()
    session = await client.create_session('Test Session')
    print(f'Session: {session}')
    print(f'ID: {session.id}')
    print(f'Title: {session.title}')
    print(f'Version: {session.version}')
    print(f'Time Created: {session.time_created}')
    print(f'Time Updated: {session.time_updated}')
    print(f'Success!')

asyncio.run(test())
