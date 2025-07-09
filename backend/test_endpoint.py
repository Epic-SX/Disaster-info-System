#!/usr/bin/env python3
"""
Test script to debug the chat messages endpoint
"""
import asyncio
import os
from main import get_chat_messages

async def test_chat_messages():
    try:
        print("Testing chat messages endpoint...")
        result = await get_chat_messages(limit=3)
        print(f"Success! Got {len(result)} messages")
        for msg in result:
            print(f"- {msg.author}: {msg.message[:50]}...")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat_messages()) 