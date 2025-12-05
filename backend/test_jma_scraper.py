#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for JMA tsunami scraper
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from jma_tsunami_scraper import get_jma_tsunami_status

async def test():
    print("Testing JMA tsunami scraper...")
    try:
        status = await get_jma_tsunami_status(headless=True)
        if status:
            print(f"\n✅ Success!")
            print(f"Message: {status.message}")
            print(f"Has Warning: {status.has_warning}")
            print(f"Warning Type: {status.warning_type}")
            print(f"Affected Areas: {status.affected_areas}")
            print(f"Timestamp: {status.timestamp}")
        else:
            print("\n❌ Scraper returned None")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())


