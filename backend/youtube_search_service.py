#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced YouTube Search Service using SerpApi
Provides comprehensive YouTube video search capabilities for disaster-related content
Uses SerpApi's YouTube Search API, YouTube Video API, and Video Results API
"""

import os
import logging
import requests
import asyncio
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class YouTubeVideo:
    """Enhanced YouTube video data class"""
    video_id: str
    title: str
    channel: str
    description: str
    thumbnail: str
    duration: str
    views: str
    published_time: str
    link: str
    # Additional metadata
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    subscriber_count: Optional[str] = None
    video_type: Optional[str] = None  # 'video', 'short', 'live'
    verified_channel: bool = False
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

@dataclass
class YouTubeChannel:
    """YouTube channel information"""
    channel_id: str
    name: str
    url: str
    thumbnail: str
    subscriber_count: str
    verified: bool = False
    description: Optional[str] = None

@dataclass
class YouTubeSearchResult:
    """Enhanced YouTube search result container"""
    videos: List[YouTubeVideo]
    channels: List[YouTubeChannel] = field(default_factory=list)
    total_results: int = 0
    search_query: str = ""
    next_page_token: Optional[str] = None
    related_searches: List[str] = field(default_factory=list)
    search_parameters: Dict = field(default_factory=dict)
    response_time: float = 0.0

class YouTubeSearchService:
    """Enhanced YouTube search service using SerpApi"""
    
    def __init__(self):
        # API Configuration
        self.api_key = os.getenv('SERPAPI_API_KEY') or os.getenv('SERPAPI_KEY')
        self.base_url = os.getenv('SERPAPI_BASE_URL', 'https://serpapi.com/search.json')
        
        if not self.api_key:
            logger.warning("SERPAPI_API_KEY not found in environment variables")
            
        # Enhanced disaster-related search terms (Japanese and English)
        self.disaster_search_terms = {
            'earthquake': [
                "地震 最新情報", "earthquake latest news", "地震速報", "earthquake alert",
                "震度", "seismic intensity", "震源", "epicenter", "余震", "aftershock"
            ],
            'tsunami': [
                "津波 警報", "tsunami warning", "津波注意報", "tsunami advisory",
                "津波情報", "tsunami information", "高潮", "storm surge"
            ],
            'typhoon': [
                "台風 進路", "typhoon track", "台風情報", "typhoon information",
                "台風予報", "typhoon forecast", "暴風", "strong wind"
            ],
            'disaster_prep': [
                "災害 対策", "disaster preparedness", "防災グッズ", "emergency kit",
                "避難 準備", "evacuation preparation", "防災 備蓄", "disaster supplies"
            ],
            'live_updates': [
                "災害 ライブ", "disaster live", "緊急放送", "emergency broadcast",
                "ニュース ライブ", "news live", "速報 ライブ", "breaking news live"
            ]
        }
        
        # Search filters for different content types
        self.search_filters = {
            'live': 'EgJAAQ%253D%253D',  # Live videos
            'today': 'CAI%253D',  # Today's uploads
            'this_week': 'CAM%253D',  # This week's uploads
            'this_month': 'CAQ%253D',  # This month's uploads
            'hd': 'EgIgAQ%253D%253D',  # HD videos
            '4k': 'EgJwAQ%253D%253D',  # 4K videos
            'short': 'EgQQARgB',  # YouTube Shorts
            'long': 'EgQQAhgB',  # Long videos (>20 minutes)
            'channel': 'EgIQAg%253D%253D',  # Channels
            'playlist': 'EgIQAw%253D%253D'  # Playlists
        }
        
    async def search_disaster_videos(self, 
                                   query: str = None, 
                                   limit: int = 10,
                                   search_type: str = 'general',
                                   time_filter: str = None,
                                   quality_filter: str = None,
                                   include_shorts: bool = True) -> YouTubeSearchResult:
        """
        Enhanced search for disaster-related YouTube videos
        
        Args:
            query: Search query. If None, uses default disaster terms
            limit: Maximum number of results to return
            search_type: Type of search ('general', 'live', 'recent', 'channels')
            time_filter: Time filter ('today', 'this_week', 'this_month')
            quality_filter: Quality filter ('hd', '4k')
            include_shorts: Whether to include YouTube Shorts
            
        Returns:
            YouTubeSearchResult containing video information
        """
        if not self.api_key:
            logger.error("SerpApi API key not configured")
            return YouTubeSearchResult(videos=[], search_query=query or "")
            
        # Prepare search query
        search_query = query or self._get_default_disaster_query(search_type)
        
        start_time = datetime.now()
        
        try:
            # Build search parameters
            params = {
                'engine': 'youtube',
                'search_query': search_query,
                'api_key': self.api_key,
                'num': min(limit, 100),  # SerpApi limit
                'gl': 'jp',  # Japan for disaster-related content
                'hl': 'ja'   # Japanese language
            }
            
            # Apply filters
            sp_filters = []
            
            if search_type == 'live':
                sp_filters.append(self.search_filters['live'])
            elif search_type == 'channels':
                sp_filters.append(self.search_filters['channel'])
                
            if time_filter and time_filter in self.search_filters:
                sp_filters.append(self.search_filters[time_filter])
                
            if quality_filter and quality_filter in self.search_filters:
                sp_filters.append(self.search_filters[quality_filter])
                
            if not include_shorts:
                # Exclude shorts (no direct filter, but we'll filter in results)
                pass
                
            if sp_filters:
                # Combine filters (this is simplified - real YouTube uses complex encoding)
                params['sp'] = sp_filters[0]  # Use first filter for now
            
            logger.info(f"Making SerpAPI request with params: {params}")
            
            # Make API request
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Log response structure for debugging
            logger.info(f"SerpAPI response keys: {list(data.keys())}")
            if 'video_results' in data:
                logger.info(f"Found {len(data['video_results'])} video results")
            elif 'videos' in data:
                logger.info(f"Found {len(data['videos'])} videos")
            else:
                logger.warning("No video results found in response")
            
            # Log a sample of the response for debugging
            if 'video_results' in data and data['video_results']:
                logger.info(f"Sample video result: {data['video_results'][0]}")
            elif 'videos' in data and data['videos']:
                logger.info(f"Sample video: {data['videos'][0]}")
            
            # Check for error in response
            if 'error' in data:
                logger.error(f"SerpAPI error: {data['error']}")
                return YouTubeSearchResult(videos=[], search_query=search_query)
            
            # Parse response
            result = self._parse_search_response(data, search_query, include_shorts)
            
            # Calculate response time
            result.response_time = (datetime.now() - start_time).total_seconds()
            result.search_parameters = params
            
            logger.info(f"YouTube search completed: {len(result.videos)} videos found for '{search_query}'")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making SerpApi request: {e}")
            return YouTubeSearchResult(videos=[], search_query=search_query)
        except Exception as e:
            logger.error(f"Unexpected error in YouTube search: {e}")
            return YouTubeSearchResult(videos=[], search_query=search_query)
    
    async def get_video_details(self, video_id: str) -> Optional[YouTubeVideo]:
        """
        Get detailed information about a specific YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTubeVideo with detailed information or None if error
        """
        if not self.api_key:
            logger.error("SerpApi API key not configured")
            return None
        
        try:
            params = {
                'engine': 'youtube_video',
                'v': video_id,
                'api_key': self.api_key,
                'gl': 'jp',
                'hl': 'ja'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse video details
            return self._parse_video_details(data)
            
        except Exception as e:
            logger.error(f"Error getting video details for {video_id}: {e}")
            return None
    
    async def search_live_disaster_streams(self, location: str = "Japan") -> YouTubeSearchResult:
        """Enhanced search for live disaster-related streams"""
        
        live_queries = [
            f"災害 ライブ配信 {location}",
            f"地震 ライブ {location}",
            f"津波 ライブ配信",
            f"台風 ライブ情報 {location}",
            f"emergency broadcast {location}",
            f"disaster live stream {location}"
        ]
        
        all_videos = []
        all_channels = []
        
        for query in live_queries[:3]:  # Limit to avoid API quota issues
            try:
                result = await self.search_disaster_videos(
                    query=query,
                    limit=10,
                    search_type='live'
                )
                all_videos.extend(result.videos)
                all_channels.extend(result.channels)
                
                # Add delay to respect API limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error searching live streams with query '{query}': {e}")
                continue
            
        # Remove duplicates
        unique_videos = self._deduplicate_videos(all_videos)
        unique_channels = self._deduplicate_channels(all_channels)
        
        return YouTubeSearchResult(
            videos=unique_videos,
            channels=unique_channels,
            total_results=len(unique_videos),
            search_query=f"Live disaster streams - {location}"
        )
    
    async def get_trending_disaster_topics(self, region: str = "JP") -> List[Dict]:
        """Get trending disaster-related topics from YouTube"""
        
        trending_topics = []
        
        try:
            # Search for recent disaster content to identify trends
            recent_query = "災害 OR 地震 OR 津波 OR 台風"
            
            params = {
                'engine': 'youtube',
                'search_query': recent_query,
                'api_key': self.api_key,
                'sp': self.search_filters['today'],  # Today's uploads
                'num': 50,
                'gl': region.lower(),
                'hl': 'ja'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract trending topics from titles and related searches
            video_results = data.get('video_results', [])
            related_searches = data.get('related_searches', [])
            
            # Analyze video titles for trending keywords
            title_keywords = self._extract_trending_keywords(video_results)
            
            # Add related searches
            for search in related_searches:
                trending_topics.append({
                    'query': search.get('query', ''),
                    'link': search.get('link', ''),
                    'thumbnail': search.get('thumbnail', ''),
                    'type': 'related_search'
                })
            
            # Add trending keywords
            for keyword, count in title_keywords.items():
                trending_topics.append({
                    'query': keyword,
                    'count': count,
                    'type': 'trending_keyword'
                })
            
            return trending_topics[:20]  # Return top 20 trending topics
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []
    
    async def search_disaster_channels(self, limit: int = 10) -> YouTubeSearchResult:
        """Search for disaster information and news channels"""
        
        channel_queries = [
            "災害情報 チャンネル",
            "地震情報 チャンネル", 
            "防災 チャンネル",
            "緊急放送 チャンネル",
            "disaster information channel",
            "emergency broadcast channel"
        ]
        
        all_channels = []
        
        for query in channel_queries:
            try:
                params = {
                    'engine': 'youtube',
                    'search_query': query,
                    'api_key': self.api_key,
                    'sp': self.search_filters['channel'],
                    'num': 20,
                    'gl': 'jp',
                    'hl': 'ja'
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Parse channel results
                channel_results = data.get('channel_results', [])
                for channel_data in channel_results:
                    channel = self._parse_channel_data(channel_data)
                    if channel:
                        all_channels.append(channel)
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error searching channels with query '{query}': {e}")
                continue
        
        # Remove duplicates and sort by subscriber count
        unique_channels = self._deduplicate_channels(all_channels)
        unique_channels.sort(key=lambda x: self._parse_subscriber_count(x.subscriber_count), reverse=True)
        
        return YouTubeSearchResult(
            videos=[],
            channels=unique_channels[:limit],
            total_results=len(unique_channels),
            search_query="Disaster information channels"
        )
    
    async def search_by_location(self, location: str, disaster_type: str = None, limit: int = 20) -> YouTubeSearchResult:
        """Search for disaster content specific to a location"""
        
        if disaster_type and disaster_type in self.disaster_search_terms:
            base_terms = self.disaster_search_terms[disaster_type]
        else:
            base_terms = ["災害", "緊急情報", "disaster", "emergency"]
        
        location_queries = [f"{term} {location}" for term in base_terms[:5]]
        
        all_videos = []
        
        for query in location_queries:
            try:
                result = await self.search_disaster_videos(
                    query=query,
                    limit=max(5, limit // len(location_queries)),
                    time_filter='this_week'
                )
                all_videos.extend(result.videos)
                
                await asyncio.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error searching location-specific content: {e}")
                continue
        
        unique_videos = self._deduplicate_videos(all_videos)
        
        return YouTubeSearchResult(
            videos=unique_videos[:limit],
            total_results=len(unique_videos),
            search_query=f"Disaster content for {location}"
        )
    
    def _parse_search_response(self, data: Dict, search_query: str, include_shorts: bool = True) -> YouTubeSearchResult:
        """Parse SerpApi search response into YouTubeSearchResult"""
        
        videos = []
        channels = []
        
        # Parse video results - check multiple possible keys based on SerpAPI documentation
        video_results = data.get('video_results', [])
        if not video_results:
            # Try alternative keys based on SerpAPI documentation
            video_results = data.get('videos', [])
        
        logger.info(f"Found {len(video_results)} video results to parse")
        
        for video_data in video_results:
            try:
                video = self._parse_video_data(video_data)
                if video:
                    # Filter out shorts if requested
                    if not include_shorts and self._is_youtube_short(video):
                        continue
                    videos.append(video)
            except Exception as e:
                logger.warning(f"Error parsing video data: {e}")
                continue
        
        # Parse channel results if present
        channel_results = data.get('channel_results', [])
        logger.info(f"Found {len(channel_results)} channel results to parse")
        
        for channel_data in channel_results:
            try:
                channel = self._parse_channel_data(channel_data)
                if channel:
                    channels.append(channel)
            except Exception as e:
                logger.warning(f"Error parsing channel data: {e}")
                continue
        
        # Extract related searches - handle the actual SerpAPI structure
        related_searches = []
        
        # Check for searches_related_to_star_wars (this is the actual key from SerpAPI)
        searches_related = data.get('searches_related_to_star_wars', {})
        if searches_related and 'searches' in searches_related:
            for search in searches_related['searches']:
                if 'query' in search:
                    related_searches.append(search['query'])
        
        # Also check for general related_searches
        if not related_searches:
            for search in data.get('related_searches', []):
                if isinstance(search, dict) and 'query' in search:
                    related_searches.append(search['query'])
        
        # Get total results from search information
        search_info = data.get('search_information', {})
        total_results = search_info.get('total_results', len(videos) + len(channels))
        
        # Get pagination info
        pagination = data.get('serpapi_pagination', {})
        next_page_token = pagination.get('next_page_token')
        
        logger.info(f"Parsed {len(videos)} videos and {len(channels)} channels from SerpAPI response")
        logger.info(f"Total results: {total_results}, Related searches: {len(related_searches)}")
        
        return YouTubeSearchResult(
            videos=videos,
            channels=channels,
            total_results=total_results,
            search_query=search_query,
            next_page_token=next_page_token,
            related_searches=related_searches
        )
    
    def _parse_video_data(self, video_data: Dict) -> Optional[YouTubeVideo]:
        """Parse individual video data from SerpApi response"""
        
        try:
            link = video_data.get('link', '')
            video_id = self._extract_video_id(link)
            
            # Extract channel information - handle both object and string formats
            channel_info = video_data.get('channel', {})
            if isinstance(channel_info, dict):
                channel_name = channel_info.get('name', '')
                channel_id = channel_info.get('id', '')
                channel_url = channel_info.get('link', '')
                subscriber_count = channel_info.get('subscribers', '')
                verified = channel_info.get('verified', False)
            else:
                channel_name = str(channel_info) if channel_info else ''
                channel_id = ''
                channel_url = ''
                subscriber_count = ''
                verified = False
            
            # Handle thumbnail - could be string or object
            thumbnail = video_data.get('thumbnail', '')
            if isinstance(thumbnail, dict):
                thumbnail = thumbnail.get('static', '') or thumbnail.get('rich', '')
            
            # Determine video type
            video_type = self._determine_video_type(video_data)
            
            return YouTubeVideo(
                video_id=video_id,
                title=video_data.get('title', ''),
                channel=channel_name,
                description=video_data.get('description', ''),
                thumbnail=thumbnail,
                duration=video_data.get('length', ''),  # SerpAPI uses 'length' instead of 'duration'
                views=video_data.get('views', ''),
                published_time=video_data.get('published_date', ''),  # SerpAPI uses 'published_date'
                link=link,
                channel_id=channel_id,
                channel_url=channel_url,
                subscriber_count=subscriber_count,
                verified_channel=verified,
                video_type=video_type
            )
            
        except Exception as e:
            logger.error(f"Error parsing video data: {e}")
            return None
    
    def _parse_channel_data(self, channel_data: Dict) -> Optional[YouTubeChannel]:
        """Parse channel data from SerpApi response"""
        
        try:
            return YouTubeChannel(
                channel_id=channel_data.get('id', ''),
                name=channel_data.get('title', ''),
                url=channel_data.get('link', ''),
                thumbnail=channel_data.get('thumbnail', ''),
                subscriber_count=channel_data.get('subscribers', ''),
                verified=channel_data.get('verified', False),
                description=channel_data.get('description', '')
            )
        except Exception as e:
            logger.error(f"Error parsing channel data: {e}")
            return None
    
    def _parse_video_details(self, data: Dict) -> Optional[YouTubeVideo]:
        """Parse detailed video information from YouTube Video API"""
        
        try:
            video_info = data.get('video_info', {})
            channel_info = data.get('channel_info', {})
            
            return YouTubeVideo(
                video_id=video_info.get('id', ''),
                title=video_info.get('title', ''),
                channel=channel_info.get('name', ''),
                description=video_info.get('description', ''),
                thumbnail=video_info.get('thumbnail', ''),
                duration=video_info.get('duration', ''),
                views=video_info.get('views', ''),
                published_time=video_info.get('published_date', ''),
                link=video_info.get('url', ''),
                channel_id=channel_info.get('id', ''),
                channel_url=channel_info.get('url', ''),
                subscriber_count=channel_info.get('subscribers', ''),
                verified_channel=channel_info.get('verified', False),
                category=video_info.get('category', ''),
                tags=video_info.get('tags', [])
            )
            
        except Exception as e:
            logger.error(f"Error parsing video details: {e}")
            return None
    
    def _get_default_disaster_query(self, search_type: str) -> str:
        """Get default search query based on search type"""
        
        if search_type == 'live':
            return "災害 ライブ配信 OR 地震 ライブ OR 緊急放送"
        elif search_type == 'recent':
            return "災害 最新情報 OR 地震 速報 OR 津波 警報"
        elif search_type == 'channels':
            return "災害情報 チャンネル OR 防災 チャンネル"
        else:
            return "災害 情報 OR 地震 OR 津波 OR 台風"
    
    def _extract_video_id(self, youtube_url: str) -> str:
        """Extract video ID from YouTube URL"""
        try:
            if 'watch?v=' in youtube_url:
                return youtube_url.split('watch?v=')[1].split('&')[0]
            elif 'youtu.be/' in youtube_url:
                return youtube_url.split('youtu.be/')[1].split('?')[0]
            elif '/shorts/' in youtube_url:
                return youtube_url.split('/shorts/')[1].split('?')[0]
            else:
                return ''
        except Exception:
            return ''
    
    def _determine_video_type(self, video_data: Dict) -> str:
        """Determine video type (video, short, live)"""
        
        link = video_data.get('link', '')
        duration = video_data.get('duration', '')
        
        if '/shorts/' in link:
            return 'short'
        elif duration and ('LIVE' in duration.upper() or 'ライブ' in duration):
            return 'live'
        else:
            return 'video'
    
    def _is_youtube_short(self, video: YouTubeVideo) -> bool:
        """Check if video is a YouTube Short"""
        return (video.video_type == 'short' or 
                '/shorts/' in video.link or
                (video.duration and self._duration_to_seconds(video.duration) <= 60))
    
    def _duration_to_seconds(self, duration: str) -> int:
        """Convert duration string to seconds"""
        try:
            if ':' not in duration:
                return 0
            parts = duration.split(':')
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            return 0
        return 0
    
    def _deduplicate_videos(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Remove duplicate videos by video_id"""
        seen = set()
        unique_videos = []
        
        for video in videos:
            if video.video_id and video.video_id not in seen:
                seen.add(video.video_id)
                unique_videos.append(video)
        
        return unique_videos
    
    def _deduplicate_channels(self, channels: List[YouTubeChannel]) -> List[YouTubeChannel]:
        """Remove duplicate channels by channel_id"""
        seen = set()
        unique_channels = []
        
        for channel in channels:
            if channel.channel_id and channel.channel_id not in seen:
                seen.add(channel.channel_id)
                unique_channels.append(channel)
        
        return unique_channels
    
    def _extract_trending_keywords(self, video_results: List[Dict]) -> Dict[str, int]:
        """Extract trending keywords from video titles"""
        
        keyword_count = {}
        disaster_keywords = [
            '地震', '津波', '台風', '災害', '避難', '警報', '緊急',
            'earthquake', 'tsunami', 'typhoon', 'disaster', 'emergency'
        ]
        
        for video in video_results:
            title = video.get('title', '').lower()
            for keyword in disaster_keywords:
                if keyword in title:
                    keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
        
        # Sort by frequency
        return dict(sorted(keyword_count.items(), key=lambda x: x[1], reverse=True))
    
    def _parse_subscriber_count(self, subscriber_str: str) -> int:
        """Parse subscriber count string to integer for sorting"""
        try:
            if not subscriber_str:
                return 0
            
            # Remove non-numeric characters except K, M, B
            clean_str = ''.join(c for c in subscriber_str if c.isdigit() or c in 'KMB.')
            
            if 'K' in clean_str:
                return int(float(clean_str.replace('K', '')) * 1000)
            elif 'M' in clean_str:
                return int(float(clean_str.replace('M', '')) * 1000000)
            elif 'B' in clean_str:
                return int(float(clean_str.replace('B', '')) * 1000000000)
            else:
                return int(clean_str) if clean_str.isdigit() else 0
        except:
            return 0

# Example usage and testing
async def main():
    """Test the enhanced YouTube search service"""
    search_service = YouTubeSearchService()
    
    print("Testing enhanced YouTube search service...")
    
    # Test 1: General disaster video search
    print("\n1. Testing disaster video search...")
    result = await search_service.search_disaster_videos("地震 最新", 5)
    print(f"Found {result.total_results} videos for '地震 最新'")
    for video in result.videos[:3]:
        print(f"- {video.title} by {video.channel} ({video.video_type})")
    
    # Test 2: Live stream search
    print("\n2. Testing live stream search...")
    live_result = await search_service.search_live_disaster_streams()
    print(f"Found {live_result.total_results} live streams")
    for video in live_result.videos[:3]:
        print(f"- {video.title} by {video.channel} ({video.duration})")
    
    # Test 3: Channel search
    print("\n3. Testing disaster channel search...")
    channel_result = await search_service.search_disaster_channels(5)
    print(f"Found {len(channel_result.channels)} disaster channels")
    for channel in channel_result.channels[:3]:
        print(f"- {channel.name} ({channel.subscriber_count} subscribers)")
    
    # Test 4: Location-specific search
    print("\n4. Testing location-specific search...")
    location_result = await search_service.search_by_location("東京", "earthquake", 5)
    print(f"Found {location_result.total_results} Tokyo earthquake videos")
    for video in location_result.videos[:3]:
        print(f"- {video.title} by {video.channel}")
    
    # Test 5: Trending topics
    print("\n5. Testing trending topics...")
    trending = await search_service.get_trending_disaster_topics()
    print(f"Found {len(trending)} trending topics")
    for topic in trending[:5]:
        print(f"- {topic.get('query', 'N/A')} ({topic.get('type', 'unknown')})")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 