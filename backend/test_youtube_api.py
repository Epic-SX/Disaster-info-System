#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for YouTube Data API v3 integration
Tests the new YouTube search service implementation
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_search_service import YouTubeSearchService

async def test_youtube_api():
    """Test the YouTube Data API v3 implementation"""
    
    print("=" * 80)
    print("YouTube Data API v3 Integration Test")
    print("=" * 80)
    print()
    
    # Initialize the service
    service = YouTubeSearchService()
    print(f"✓ YouTube Search Service initialized")
    print(f"  API Key configured: {'Yes' if service.api_key else 'No'}")
    print(f"  Base URL: {service.base_url}")
    print()
    
    # Test 1: Basic disaster video search
    print("Test 1: Basic Disaster Video Search")
    print("-" * 80)
    try:
        result = await service.search_disaster_videos(
            query="地震 最新情報",
            limit=5,
            search_type="general"
        )
        print(f"✓ Search completed successfully")
        print(f"  Query: '地震 最新情報'")
        print(f"  Found: {result.total_results} total results")
        print(f"  Returned: {len(result.videos)} videos")
        print(f"  Response time: {result.response_time:.2f} seconds")
        print()
        
        if result.videos:
            print("  Sample video:")
            video = result.videos[0]
            print(f"    - Title: {video.title[:60]}...")
            print(f"    - Channel: {video.channel}")
            print(f"    - Views: {video.views}")
            print(f"    - Duration: {video.duration}")
            print(f"    - Published: {video.published_time}")
            print(f"    - Type: {video.video_type}")
            print(f"    - Link: {video.link}")
        print()
    except Exception as e:
        print(f"✗ Search failed: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Test 2: Live stream search
    print("Test 2: Live Stream Search")
    print("-" * 80)
    try:
        result = await service.search_disaster_videos(
            query="地震 ライブ",
            limit=3,
            search_type="live"
        )
        print(f"✓ Live search completed successfully")
        print(f"  Found: {len(result.videos)} live streams")
        if result.videos:
            for i, video in enumerate(result.videos, 1):
                print(f"  {i}. {video.title[:50]}... ({video.channel})")
        else:
            print("  No live streams found at this time")
        print()
    except Exception as e:
        print(f"✗ Live search failed: {e}")
        print()
    
    # Test 3: Channel search
    print("Test 3: Disaster Channel Search")
    print("-" * 80)
    try:
        result = await service.search_disaster_channels(limit=3)
        print(f"✓ Channel search completed successfully")
        print(f"  Found: {len(result.channels)} channels")
        if result.channels:
            for i, channel in enumerate(result.channels, 1):
                print(f"  {i}. {channel.name}")
                print(f"     Subscribers: {channel.subscriber_count}")
                print(f"     URL: {channel.url}")
        print()
    except Exception as e:
        print(f"✗ Channel search failed: {e}")
        print()
    
    # Test 4: Video details lookup
    print("Test 4: Video Details Lookup")
    print("-" * 80)
    try:
        # Get a video ID from the first search
        result = await service.search_disaster_videos(query="地震", limit=1)
        if result.videos:
            video_id = result.videos[0].video_id
            print(f"  Testing with video ID: {video_id}")
            
            video = await service.get_video_details(video_id)
            if video:
                print(f"✓ Video details retrieved successfully")
                print(f"  Title: {video.title}")
                print(f"  Channel: {video.channel}")
                print(f"  Views: {video.views}")
                print(f"  Duration: {video.duration}")
                print(f"  Description: {video.description[:100]}...")
            else:
                print(f"✗ Failed to retrieve video details")
        else:
            print("  No videos available for testing")
        print()
    except Exception as e:
        print(f"✗ Video details lookup failed: {e}")
        print()
    
    # Test 5: Trending topics
    print("Test 5: Trending Disaster Topics")
    print("-" * 80)
    try:
        topics = await service.get_trending_disaster_topics()
        print(f"✓ Trending topics retrieved successfully")
        print(f"  Found: {len(topics)} trending topics")
        if topics:
            print("  Top 5 trending keywords:")
            for i, topic in enumerate(topics[:5], 1):
                print(f"    {i}. {topic.get('query')} (count: {topic.get('count', 'N/A')})")
        print()
    except Exception as e:
        print(f"✗ Trending topics failed: {e}")
        print()
    
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print("All tests completed. Check results above for any failures.")
    print()
    print("Note: YouTube Data API v3 is now being used instead of SerpAPI.")
    print("Make sure your API key has sufficient quota and is properly configured.")
    print()

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_youtube_api())


