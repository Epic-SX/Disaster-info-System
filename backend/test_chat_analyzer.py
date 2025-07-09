#!/usr/bin/env python3
"""Test script to debug YouTubeChatAnalyzer initialization"""

import sys
import traceback

try:
    from youtube_chat_service import YouTubeChatAnalyzer
    print("✓ Successfully imported YouTubeChatAnalyzer")
    
    try:
        analyzer = YouTubeChatAnalyzer('development_mode')
        print("✓ Successfully created YouTubeChatAnalyzer instance")
        print(f"Video ID: {analyzer.video_id}")
        print(f"Config: {analyzer.config}")
        print("SUCCESS: YouTubeChatAnalyzer initialized properly")
        
    except Exception as e:
        print(f"✗ Failed to create YouTubeChatAnalyzer instance: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
except Exception as e:
    print(f"✗ Failed to import YouTubeChatAnalyzer: {e}")
    print("Full traceback:")
    traceback.print_exc() 