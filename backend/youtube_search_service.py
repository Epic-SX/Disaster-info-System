#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Search Service using SerpApi
Provides YouTube video search capabilities for disaster-related content
"""

import os
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class YouTubeVideo:
    """YouTube video data class"""
    video_id: str
    title: str
    channel: str
    description: str
    thumbnail: str
    duration: str
    views: str
    published_time: str
    link: str

@dataclass
class YouTubeSearchResult:
    """YouTube search result container"""
    videos: List[YouTubeVideo]
    total_results: int
    search_query: str
    next_page_token: Optional[str] = None

class YouTubeSearchService:
    """YouTube search service using SerpApi"""
    
    def __init__(self):
        self.api_key = os.getenv('SERPAPI_API_KEY')
        self.base_url = os.getenv('SERPAPI_BASE_URL', 'https://serpapi.com/search.json')
        
        if not self.api_key:
            logger.warning("SERPAPI_API_KEY not found in environment variables")
            
        # Disaster-related search terms
        self.disaster_search_terms = [
            "地震 最新情報",
            "津波 警報",
            "台風 進路",
            "災害 ニュース",
            "避難 情報",
            "earthquake latest news",
            "tsunami warning",
            "typhoon track",
            "disaster news",
            "evacuation information"
        ]
        
    async def search_disaster_videos(self, query: str = None, limit: int = 10) -> YouTubeSearchResult:
        """
        Search for disaster-related YouTube videos
        
        Args:
            query: Search query. If None, uses default disaster terms
            limit: Maximum number of results to return
            
        Returns:
            YouTubeSearchResult containing video information
        """
        if not self.api_key:
            logger.error("SerpApi API key not configured")
            return YouTubeSearchResult(videos=[], total_results=0, search_query=query or "")
            
        search_query = query or "災害 地震 津波 最新情報"
        
        try:
            params = {
                'engine': 'youtube',
                'search_query': search_query,
                'api_key': self.api_key,
                'num': limit
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            videos = []
            video_results = data.get('video_results', [])
            
            for video_data in video_results:
                try:
                    video = YouTubeVideo(
                        video_id=self._extract_video_id(video_data.get('link', '')),
                        title=video_data.get('title', ''),
                        channel=video_data.get('channel', {}).get('name', ''),
                        description=video_data.get('description', ''),
                        thumbnail=video_data.get('thumbnail', ''),
                        duration=video_data.get('duration', ''),
                        views=video_data.get('views', ''),
                        published_time=video_data.get('published_time', ''),
                        link=video_data.get('link', '')
                    )
                    videos.append(video)
                except Exception as e:
                    logger.warning(f"Error parsing video data: {e}")
                    continue
            
            return YouTubeSearchResult(
                videos=videos,
                total_results=len(videos),
                search_query=search_query,
                next_page_token=data.get('serpapi_pagination', {}).get('next_page_token')
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making SerpApi request: {e}")
            return YouTubeSearchResult(videos=[], total_results=0, search_query=search_query)
        except Exception as e:
            logger.error(f"Unexpected error in YouTube search: {e}")
            return YouTubeSearchResult(videos=[], total_results=0, search_query=search_query)
    
    async def search_live_disaster_streams(self) -> YouTubeSearchResult:
        """Search for live disaster-related streams"""
        query = "災害 ライブ配信 OR 地震 ライブ OR 津波 ライブ"
        
        try:
            params = {
                'engine': 'youtube',
                'search_query': query,
                'api_key': self.api_key,
                'sp': 'eAE%253D',  # Live videos filter
                'num': 20
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            videos = []
            video_results = data.get('video_results', [])
            
            for video_data in video_results:
                try:
                    video = YouTubeVideo(
                        video_id=self._extract_video_id(video_data.get('link', '')),
                        title=video_data.get('title', ''),
                        channel=video_data.get('channel', {}).get('name', ''),
                        description=video_data.get('description', ''),
                        thumbnail=video_data.get('thumbnail', ''),
                        duration=video_data.get('duration', 'LIVE'),
                        views=video_data.get('views', ''),
                        published_time=video_data.get('published_time', ''),
                        link=video_data.get('link', '')
                    )
                    videos.append(video)
                except Exception as e:
                    logger.warning(f"Error parsing live video data: {e}")
                    continue
            
            return YouTubeSearchResult(
                videos=videos,
                total_results=len(videos),
                search_query=query
            )
            
        except Exception as e:
            logger.error(f"Error searching live streams: {e}")
            return YouTubeSearchResult(videos=[], total_results=0, search_query=query)
    
    async def get_trending_disaster_topics(self) -> List[Dict]:
        """Get trending disaster-related topics from YouTube"""
        trending_topics = []
        
        try:
            params = {
                'engine': 'youtube',
                'search_query': '災害',
                'api_key': self.api_key,
                'num': 10
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract related searches and suggested searches
            related_searches = data.get('related_searches', [])
            for search in related_searches:
                trending_topics.append({
                    'query': search.get('query', ''),
                    'link': search.get('link', ''),
                    'thumbnail': search.get('thumbnail', '')
                })
            
            return trending_topics
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []
    
    def _extract_video_id(self, youtube_url: str) -> str:
        """Extract video ID from YouTube URL"""
        try:
            if 'watch?v=' in youtube_url:
                return youtube_url.split('watch?v=')[1].split('&')[0]
            elif 'youtu.be/' in youtube_url:
                return youtube_url.split('youtu.be/')[1].split('?')[0]
            else:
                return ''
        except Exception:
            return ''
    
    async def search_videos_by_keywords(self, keywords: List[str], limit: int = 5) -> Dict[str, YouTubeSearchResult]:
        """
        Search for videos using multiple keywords
        
        Args:
            keywords: List of search keywords
            limit: Maximum results per keyword
            
        Returns:
            Dictionary mapping keywords to search results
        """
        results = {}
        
        for keyword in keywords:
            try:
                result = await self.search_disaster_videos(keyword, limit)
                results[keyword] = result
            except Exception as e:
                logger.error(f"Error searching for keyword '{keyword}': {e}")
                results[keyword] = YouTubeSearchResult(videos=[], total_results=0, search_query=keyword)
        
        return results

# Example usage and testing
async def main():
    """Test the YouTube search service"""
    search_service = YouTubeSearchService()
    
    # Test disaster video search
    print("Testing disaster video search...")
    result = await search_service.search_disaster_videos("地震 最新", 5)
    print(f"Found {result.total_results} videos for '地震 最新'")
    
    for video in result.videos:
        print(f"- {video.title} by {video.channel}")
    
    # Test live stream search
    print("\nTesting live stream search...")
    live_result = await search_service.search_live_disaster_streams()
    print(f"Found {live_result.total_results} live streams")
    
    for video in live_result.videos[:3]:
        print(f"- {video.title} by {video.channel} ({video.duration})")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 