#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced YouTube Search Service using YouTube Data API v3
Provides comprehensive YouTube video search capabilities for disaster-related content
Uses YouTube Data API v3 for search, videos, and channels
"""

import os
import logging
import requests
import asyncio
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlencode
import isodate

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
    """Enhanced YouTube search service using YouTube Data API v3"""
    
    def __init__(self):
        # API Configuration - YouTube Data API v3
        # Try to get API key from environment variable first, then fallback to default
        self.api_key = os.getenv('YOUTUBE_API_KEY', 'AIzaSyDK9PqY_HUJCHz2KbVTWnU07v0S-CWLJG0')
        self.base_url = 'https://www.googleapis.com/youtube/v3'
        
        # Track API key status to reduce log spam
        self._api_key_validated = False
        self._api_key_invalid = False
        self._last_error_time = None
        self._quota_exceeded = False
        self._quota_exceeded_time = None
        
        # Caching to reduce API requests
        self._cache = {}  # Key: (method, args), Value: (result, expiry_time)
        self._cache_ttl = {
            'search': 300,  # 5 minutes for searches
            'channels': 1800,  # 30 minutes for channel searches
            'trending': 3600,  # 1 hour for trending topics
            'live': 180,  # 3 minutes for live streams
            'details': 600  # 10 minutes for video/channel details
        }
        
        if not self.api_key:
            logger.error("No YouTube API key configured! Set YOUTUBE_API_KEY environment variable.")
            logger.error("See GET_YOUTUBE_API_KEY.md for instructions on getting your own key.")
            self._api_key_invalid = True
        elif self.api_key == 'AIzaSyDK9PqY_HUJCHz2KbVTWnU07v0S-CWLJG0':
            logger.warning("⚠️  Using default YouTube API key which may not work.")
            logger.warning("📝 Get your own free API key: https://console.cloud.google.com/")
            logger.warning("📚 Instructions: See GET_YOUTUBE_API_KEY.md")
            logger.warning("🔧 Setup: Run ./setup_youtube_api_key.sh YOUR_API_KEY")
            
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
        
        # Time filters for YouTube Data API
        self.time_filters = {
            'today': (datetime.now() - timedelta(days=1)).isoformat() + 'Z',
            'this_week': (datetime.now() - timedelta(days=7)).isoformat() + 'Z',
            'this_month': (datetime.now() - timedelta(days=30)).isoformat() + 'Z'
        }
        
        # Video definition filters
        self.definition_filters = {
            'hd': 'high',
            '4k': 'high',
            'all': 'any'
        }
        
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate a cache key from method name and arguments"""
        import hashlib
        import json
        key_data = {
            'method': method,
            'args': args,
            'kwargs': {k: v for k, v in kwargs.items() if k != 'include_shorts'}  # Exclude non-critical params
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str, cache_type: str) -> Optional[YouTubeSearchResult]:
        """Get cached result if available and not expired"""
        if cache_key not in self._cache:
            return None
        
        result, expiry_time = self._cache[cache_key]
        if datetime.now() > expiry_time:
            del self._cache[cache_key]
            return None
        
        logger.debug(f"Using cached result for {cache_type}")
        return result
    
    def _cache_result(self, cache_key: str, result: YouTubeSearchResult, cache_type: str):
        """Cache a result with appropriate TTL"""
        ttl = self._cache_ttl.get(cache_type, 300)
        expiry_time = datetime.now() + timedelta(seconds=ttl)
        self._cache[cache_key] = (result, expiry_time)
        # Limit cache size to prevent memory issues
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_cache[:20]:
                del self._cache[key]
    
    async def search_disaster_videos(self, 
                                   query: str = None, 
                                   limit: int = 10,
                                   search_type: str = 'general',
                                   time_filter: str = None,
                                   quality_filter: str = None,
                                   include_shorts: bool = True) -> YouTubeSearchResult:
        """
        Enhanced search for disaster-related YouTube videos using YouTube Data API v3
        
        Args:
            query: Search query. If None, uses default disaster terms
            limit: Maximum number of results to return (max 50 per request)
            search_type: Type of search ('general', 'live', 'recent', 'channels')
            time_filter: Time filter ('today', 'this_week', 'this_month')
            quality_filter: Quality filter ('hd', '4k')
            include_shorts: Whether to include YouTube Shorts
            
        Returns:
            YouTubeSearchResult containing video information
        """
        if not self.api_key:
            logger.error("YouTube API key not configured")
            return YouTubeSearchResult(videos=[], search_query=query or "")
        
        # Check if quota exceeded flag should be reset (daily reset)
        if self._quota_exceeded and self._quota_exceeded_time:
            hours_since_exceeded = (datetime.now() - self._quota_exceeded_time).total_seconds() / 3600
            if hours_since_exceeded >= 24:
                logger.info("Resetting quota exceeded flag (24 hours passed)")
                self._quota_exceeded = False
                self._quota_exceeded_time = None
        
        # Early exit if quota exceeded (don't make more requests)
        if self._quota_exceeded:
            logger.debug(f"Skipping YouTube search - quota exceeded")
            return YouTubeSearchResult(videos=[], search_query=query or self._get_default_disaster_query(search_type))
        
        # Early exit if API key is known to be invalid (to reduce log spam)
        if self._api_key_invalid:
            # Only log at debug level after initial error has been logged
            logger.debug(f"Skipping YouTube search for '{query or search_type}' - API key invalid (check logs above for fix)")
            return YouTubeSearchResult(videos=[], search_query=query or self._get_default_disaster_query(search_type))
        
        # Check cache first
        cache_key = self._get_cache_key('search_disaster_videos', query, limit, search_type, time_filter, quality_filter)
        cached_result = self._get_cached_result(cache_key, 'search')
        if cached_result:
            return cached_result
            
        # Prepare search query
        search_query = query or self._get_default_disaster_query(search_type)
        
        start_time = datetime.now()
        
        try:
            # Build search parameters for YouTube Data API
            params = {
                'part': 'snippet',
                'q': search_query,
                'key': self.api_key,
                'maxResults': min(limit, 50),  # YouTube API limit per request
                'regionCode': 'JP',  # Japan for disaster-related content
                'relevanceLanguage': 'ja',  # Japanese language
                'type': 'video' if search_type != 'channels' else 'channel',
                'order': 'date' if search_type == 'recent' else 'relevance'
            }
            
            # Apply event type filter for live videos
            if search_type == 'live':
                params['eventType'] = 'live'
                
            # Apply time filter
            if time_filter and time_filter in self.time_filters:
                params['publishedAfter'] = self.time_filters[time_filter]
                
            # Apply video definition filter
            if quality_filter and quality_filter in self.definition_filters:
                params['videoDefinition'] = self.definition_filters[quality_filter]
            
            # Only log detailed params if debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Making YouTube API request with params: {params}")
            
            # Make API request to search endpoint
            search_url = f"{self.base_url}/search"
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Mark API key as validated if we get a successful response
            if not self._api_key_validated:
                self._api_key_validated = True
                self._api_key_invalid = False
                logger.info("✅ YouTube API key validated successfully")
            
            data = response.json()
            
            # Check for errors
            if 'error' in data:
                error_info = data['error']
                error_code = error_info.get('code', 0)
                error_reason = error_info.get('errors', [{}])[0].get('reason', '')
                
                # Check for quota exceeded
                if error_code == 403 and 'quotaExceeded' in str(error_info):
                    self._quota_exceeded = True
                    self._quota_exceeded_time = datetime.now()
                    logger.error(f"YouTube API quota exceeded! Skipping further requests.")
                    logger.error(f"Quota resets daily. Consider reducing request frequency or upgrading quota.")
                    return YouTubeSearchResult(videos=[], search_query=search_query)
                
                logger.error(f"YouTube API error: {error_info}")
                return YouTubeSearchResult(videos=[], search_query=search_query)
            
            # Extract video IDs
            video_ids = []
            items = data.get('items', [])
            
            for item in items:
                if item['id'].get('kind') == 'youtube#video':
                    video_ids.append(item['id']['videoId'])
            
            logger.info(f"Found {len(video_ids)} video IDs from search")
            
            # Get detailed video information
            videos = []
            if video_ids:
                videos = await self._get_videos_details(video_ids, include_shorts)
            
            # Parse response
            result = YouTubeSearchResult(
                videos=videos,
                total_results=data.get('pageInfo', {}).get('totalResults', len(videos)),
                search_query=search_query,
                next_page_token=data.get('nextPageToken'),
                response_time=(datetime.now() - start_time).total_seconds(),
                search_parameters=params
            )
            
            logger.info(f"YouTube search completed: {len(result.videos)} videos found for '{search_query}'")
            
            # Cache the result
            self._cache_result(cache_key, result, 'search')
            
            return result
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                # Check if it's a quota exceeded error
                if "quota" in error_msg.lower() or "quotaExceeded" in error_msg:
                    self._quota_exceeded = True
                    self._quota_exceeded_time = datetime.now()
                    logger.error(f"YouTube API quota exceeded! Skipping further requests.")
                    logger.error(f"Quota resets daily. Consider reducing request frequency or upgrading quota.")
                    return YouTubeSearchResult(videos=[], search_query=search_query)
                
                # Only log detailed error message once or every 5 minutes
                current_time = datetime.now()
                should_log_details = (
                    not self._api_key_invalid or 
                    not self._last_error_time or
                    (current_time - self._last_error_time).total_seconds() > 300
                )
                
                if should_log_details:
                    logger.error(f"YouTube API returned 403 Forbidden - API key issue!")
                    logger.error(f"❌ The API key is invalid, expired, or quota exceeded")
                    logger.error(f"🔑 Get a new key: https://console.cloud.google.com/")
                    logger.error(f"📝 See: GET_YOUTUBE_API_KEY.md for instructions")
                    logger.error(f"🔧 Run: ./setup_youtube_api_key.sh YOUR_NEW_KEY")
                    self._api_key_invalid = True
                    self._last_error_time = current_time
                else:
                    # Reduce log spam - only log at debug level after initial error
                    logger.debug(f"YouTube API 403 Forbidden (API key invalid - check logs above for fix instructions)")
            else:
                logger.error(f"Error making YouTube API request: {e}")
            return YouTubeSearchResult(videos=[], search_query=search_query)
        except Exception as e:
            logger.error(f"Unexpected error in YouTube search: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return YouTubeSearchResult(videos=[], search_query=search_query)
    
    async def _get_videos_details(self, video_ids: List[str], include_shorts: bool = True) -> List[YouTubeVideo]:
        """
        Get detailed information for multiple videos using YouTube Data API v3
        
        Args:
            video_ids: List of YouTube video IDs
            include_shorts: Whether to include YouTube Shorts
            
        Returns:
            List of YouTubeVideo objects with detailed information
        """
        if not video_ids:
            return []
        
        try:
            # YouTube API allows up to 50 video IDs per request
            params = {
                'part': 'snippet,contentDetails,statistics,liveStreamingDetails',
                'id': ','.join(video_ids),
                'key': self.api_key
            }
            
            videos_url = f"{self.base_url}/videos"
            response = requests.get(videos_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            videos = []
            for item in data.get('items', []):
                video = self._parse_video_data_youtube_api(item)
                if video:
                    # Filter out shorts if requested
                    if not include_shorts and self._is_youtube_short(video):
                        continue
                    videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.error(f"Error getting video details: {e}")
            return []
    
    async def get_video_details(self, video_id: str) -> Optional[YouTubeVideo]:
        """
        Get detailed information about a specific YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTubeVideo with detailed information or None if error
        """
        if not self.api_key:
            logger.error("YouTube API key not configured")
            return None
        
        try:
            videos = await self._get_videos_details([video_id])
            return videos[0] if videos else None
            
        except Exception as e:
            logger.error(f"Error getting video details for {video_id}: {e}")
            return None
    
    async def search_live_disaster_streams(self, location: str = "Japan") -> YouTubeSearchResult:
        """Enhanced search for live disaster-related streams"""
        
        # Check if quota exceeded flag should be reset (daily reset)
        if self._quota_exceeded and self._quota_exceeded_time:
            hours_since_exceeded = (datetime.now() - self._quota_exceeded_time).total_seconds() / 3600
            if hours_since_exceeded >= 24:
                logger.info("Resetting quota exceeded flag (24 hours passed)")
                self._quota_exceeded = False
                self._quota_exceeded_time = None
        
        # Early exit if quota exceeded
        if self._quota_exceeded:
            logger.debug("Skipping live stream search - quota exceeded")
            return YouTubeSearchResult(videos=[], search_query=f"Live disaster streams - {location}")
        
        # Check cache
        cache_key = self._get_cache_key('search_live_disaster_streams', location)
        cached_result = self._get_cached_result(cache_key, 'live')
        if cached_result:
            return cached_result
        
        # Reduce to single most relevant query to save quota
        live_queries = [
            f"災害 ライブ配信 {location}",
        ]
        
        all_videos = []
        all_channels = []
        
        for query in live_queries[:1]:  # Reduced from 3 to 1 to save quota
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
        
        result = YouTubeSearchResult(
            videos=unique_videos,
            channels=unique_channels,
            total_results=len(unique_videos),
            search_query=f"Live disaster streams - {location}"
        )
        
        # Cache the result
        self._cache_result(cache_key, result, 'live')
        
        return result
    
    async def get_trending_disaster_topics(self, region: str = "JP") -> List[Dict]:
        """Get trending disaster-related topics from YouTube using YouTube Data API v3"""
        
        # Check if quota exceeded flag should be reset (daily reset)
        if self._quota_exceeded and self._quota_exceeded_time:
            hours_since_exceeded = (datetime.now() - self._quota_exceeded_time).total_seconds() / 3600
            if hours_since_exceeded >= 24:
                logger.info("Resetting quota exceeded flag (24 hours passed)")
                self._quota_exceeded = False
                self._quota_exceeded_time = None
        
        # Early exit if quota exceeded
        if self._quota_exceeded:
            logger.debug("Skipping trending topics search - quota exceeded")
            return []
        
        trending_topics = []
        
        # Skip if API key is known to be invalid
        if self._api_key_invalid:
            logger.debug("Skipping trending topics search - API key invalid")
            return []
        
        # Check cache (trending topics returns List[Dict], not YouTubeSearchResult)
        cache_key = self._get_cache_key('get_trending_disaster_topics', region)
        if cache_key in self._cache:
            result, expiry_time = self._cache[cache_key]
            if datetime.now() <= expiry_time:
                logger.debug("Using cached trending topics")
                return result
            else:
                del self._cache[cache_key]
        
        try:
            # Search for recent disaster content to identify trends
            recent_query = "災害 OR 地震 OR 津波 OR 台風"
            
            params = {
                'part': 'snippet',
                'q': recent_query,
                'key': self.api_key,
                'maxResults': 20,  # Reduced from 50 to 20 to save quota
                'order': 'date',  # Recent videos
                'publishedAfter': self.time_filters['today'],
                'regionCode': region,
                'relevanceLanguage': 'ja',
                'type': 'video'
            }
            
            search_url = f"{self.base_url}/search"
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract trending topics from titles
            items = data.get('items', [])
            titles = [item.get('snippet', {}).get('title', '') for item in items]
            
            # Analyze video titles for trending keywords
            title_keywords = self._extract_trending_keywords_from_titles(titles)
            
            # Add trending keywords
            for keyword, count in title_keywords.items():
                trending_topics.append({
                    'query': keyword,
                    'count': count,
                    'type': 'trending_keyword'
                })
            
            result = trending_topics[:10]  # Reduced from 20 to 10 trending topics
            
            # Cache the result (trending topics is List[Dict], not YouTubeSearchResult)
            ttl = self._cache_ttl.get('trending', 3600)
            expiry_time = datetime.now() + timedelta(seconds=ttl)
            self._cache[cache_key] = (result, expiry_time)
            
            return result
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                # Use same error handling as main search method
                current_time = datetime.now()
                should_log_details = (
                    not self._api_key_invalid or 
                    not self._last_error_time or
                    (current_time - self._last_error_time).total_seconds() > 300
                )
                if should_log_details:
                    logger.error(f"YouTube API returned 403 Forbidden in trending topics search")
                    self._api_key_invalid = True
                    self._last_error_time = current_time
            else:
                logger.debug(f"Error getting trending topics: {e}")
            return []
        except Exception as e:
            logger.debug(f"Unexpected error getting trending topics: {e}")
            return []
    
    async def search_disaster_channels(self, limit: int = 10) -> YouTubeSearchResult:
        """Search for disaster information and news channels using YouTube Data API v3"""
        
        # Check if quota exceeded flag should be reset (daily reset)
        if self._quota_exceeded and self._quota_exceeded_time:
            hours_since_exceeded = (datetime.now() - self._quota_exceeded_time).total_seconds() / 3600
            if hours_since_exceeded >= 24:
                logger.info("Resetting quota exceeded flag (24 hours passed)")
                self._quota_exceeded = False
                self._quota_exceeded_time = None
        
        # Early exit if quota exceeded
        if self._quota_exceeded:
            logger.debug("Skipping channel search - quota exceeded")
            return YouTubeSearchResult(videos=[], channels=[], search_query="Disaster information channels")
        
        # Check cache
        cache_key = self._get_cache_key('search_disaster_channels', limit)
        cached_result = self._get_cached_result(cache_key, 'channels')
        if cached_result:
            return cached_result
        
        # Reduced to single most relevant query to save quota
        channel_queries = [
            "災害情報 チャンネル",
        ]
        
        all_channels = []
        
        for query in channel_queries[:1]:  # Reduced from 3 to 1 to save quota
            try:
                params = {
                    'part': 'snippet',
                    'q': query,
                    'key': self.api_key,
                    'type': 'channel',
                    'maxResults': 10,
                    'regionCode': 'JP',
                    'relevanceLanguage': 'ja'
                }
                
                search_url = f"{self.base_url}/search"
                response = requests.get(search_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract channel IDs
                channel_ids = []
                for item in data.get('items', []):
                    if item['id'].get('kind') == 'youtube#channel':
                        channel_ids.append(item['id']['channelId'])
                
                # Get detailed channel information
                if channel_ids:
                    channels = await self._get_channels_details(channel_ids)
                    all_channels.extend(channels)
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error searching channels with query '{query}': {e}")
                continue
        
        # Remove duplicates and sort by subscriber count
        unique_channels = self._deduplicate_channels(all_channels)
        unique_channels.sort(key=lambda x: self._parse_subscriber_count(x.subscriber_count), reverse=True)
        
        result = YouTubeSearchResult(
            videos=[],
            channels=unique_channels[:limit],
            total_results=len(unique_channels),
            search_query="Disaster information channels"
        )
        
        # Cache the result
        self._cache_result(cache_key, result, 'channels')
        
        return result
    
    async def search_by_location(self, location: str, disaster_type: str = None, limit: int = 20) -> YouTubeSearchResult:
        """Search for disaster content specific to a location"""
        
        # Check if quota exceeded flag should be reset (daily reset)
        if self._quota_exceeded and self._quota_exceeded_time:
            hours_since_exceeded = (datetime.now() - self._quota_exceeded_time).total_seconds() / 3600
            if hours_since_exceeded >= 24:
                logger.info("Resetting quota exceeded flag (24 hours passed)")
                self._quota_exceeded = False
                self._quota_exceeded_time = None
        
        # Early exit if quota exceeded
        if self._quota_exceeded:
            logger.debug(f"Skipping location search - quota exceeded")
            return YouTubeSearchResult(videos=[], search_query=f"Disaster content for {location}")
        
        # Check cache
        cache_key = self._get_cache_key('search_by_location', location, disaster_type, limit)
        cached_result = self._get_cached_result(cache_key, 'search')
        if cached_result:
            return cached_result
        
        if disaster_type and disaster_type in self.disaster_search_terms:
            base_terms = self.disaster_search_terms[disaster_type]
        else:
            base_terms = ["災害", "緊急情報", "disaster", "emergency"]
        
        # Reduced from 5 to 2 queries to save quota
        location_queries = [f"{term} {location}" for term in base_terms[:2]]
        
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
        
        result = YouTubeSearchResult(
            videos=unique_videos[:limit],
            total_results=len(unique_videos),
            search_query=f"Disaster content for {location}"
        )
        
        # Cache the result
        self._cache_result(cache_key, result, 'search')
        
        return result
    
    async def _get_channels_details(self, channel_ids: List[str]) -> List[YouTubeChannel]:
        """
        Get detailed information for multiple channels using YouTube Data API v3
        
        Args:
            channel_ids: List of YouTube channel IDs
            
        Returns:
            List of YouTubeChannel objects with detailed information
        """
        if not channel_ids:
            return []
        
        try:
            params = {
                'part': 'snippet,statistics',
                'id': ','.join(channel_ids),
                'key': self.api_key
            }
            
            channels_url = f"{self.base_url}/channels"
            response = requests.get(channels_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            channels = []
            for item in data.get('items', []):
                channel = self._parse_channel_data_youtube_api(item)
                if channel:
                    channels.append(channel)
            
            return channels
            
        except Exception as e:
            logger.error(f"Error getting channel details: {e}")
            return []
    
    def _parse_video_data_youtube_api(self, video_data: Dict) -> Optional[YouTubeVideo]:
        """Parse video data from YouTube Data API v3 response"""
        
        try:
            video_id = video_data.get('id', '')
            snippet = video_data.get('snippet', {})
            content_details = video_data.get('contentDetails', {})
            statistics = video_data.get('statistics', {})
            live_details = video_data.get('liveStreamingDetails', {})
            
            # Extract channel information
            channel_id = snippet.get('channelId', '')
            channel_name = snippet.get('channelTitle', '')
            channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else ''
            
            # Extract thumbnail (prefer high quality)
            thumbnails = snippet.get('thumbnails', {})
            thumbnail = (thumbnails.get('high', {}).get('url', '') or
                        thumbnails.get('medium', {}).get('url', '') or
                        thumbnails.get('default', {}).get('url', ''))
            
            # Parse duration from ISO 8601 format (e.g., PT1H2M10S)
            duration_iso = content_details.get('duration', 'PT0S')
            try:
                duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                seconds = int(duration_seconds % 60)
                if hours > 0:
                    duration = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration = f"{minutes}:{seconds:02d}"
            except:
                duration = "Unknown"
            
            # Format view count
            view_count = int(statistics.get('viewCount', 0))
            views = self._format_number(view_count)
            
            # Parse published time
            published_at = snippet.get('publishedAt', '')
            try:
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                published_time = self._format_time_ago(pub_date)
            except:
                published_time = published_at
            
            # Determine video type
            video_type = 'video'
            if live_details:
                if live_details.get('actualStartTime') and not live_details.get('actualEndTime'):
                    video_type = 'live'
            elif duration_seconds <= 60:
                video_type = 'short'
            
            # Build video link
            link = f"https://www.youtube.com/watch?v={video_id}"
            
            return YouTubeVideo(
                video_id=video_id,
                title=snippet.get('title', ''),
                channel=channel_name,
                description=snippet.get('description', ''),
                thumbnail=thumbnail,
                duration=duration,
                views=views,
                published_time=published_time,
                link=link,
                channel_id=channel_id,
                channel_url=channel_url,
                subscriber_count='',  # Not available in video endpoint
                verified_channel=False,  # Would need separate channel lookup
                video_type=video_type,
                category=snippet.get('categoryId', ''),
                tags=snippet.get('tags', [])
            )
            
        except Exception as e:
            logger.error(f"Error parsing video data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_channel_data_youtube_api(self, channel_data: Dict) -> Optional[YouTubeChannel]:
        """Parse channel data from YouTube Data API v3 response"""
        
        try:
            channel_id = channel_data.get('id', '')
            snippet = channel_data.get('snippet', {})
            statistics = channel_data.get('statistics', {})
            
            # Extract thumbnail
            thumbnails = snippet.get('thumbnails', {})
            thumbnail = (thumbnails.get('high', {}).get('url', '') or
                        thumbnails.get('medium', {}).get('url', '') or
                        thumbnails.get('default', {}).get('url', ''))
            
            # Format subscriber count
            subscriber_count_raw = int(statistics.get('subscriberCount', 0))
            subscriber_count = self._format_number(subscriber_count_raw) + ' subscribers'
            
            return YouTubeChannel(
                channel_id=channel_id,
                name=snippet.get('title', ''),
                url=f"https://www.youtube.com/channel/{channel_id}",
                thumbnail=thumbnail,
                subscriber_count=subscriber_count,
                verified=False,  # Not directly available in API response
                description=snippet.get('description', '')
            )
        except Exception as e:
            logger.error(f"Error parsing channel data: {e}")
            return None
    
    def _format_number(self, num: int) -> str:
        """Format large numbers with K, M, B suffixes"""
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)
    
    def _format_time_ago(self, pub_date: datetime) -> str:
        """Format datetime to 'X hours/days/weeks ago' format"""
        now = datetime.now(pub_date.tzinfo)
        diff = now - pub_date
        
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif seconds < 31536000:
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = int(seconds / 31536000)
            return f"{years} year{'s' if years > 1 else ''} ago"
    
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
    
    def _extract_trending_keywords_from_titles(self, titles: List[str]) -> Dict[str, int]:
        """Extract trending keywords from video titles"""
        
        keyword_count = {}
        disaster_keywords = [
            '地震', '津波', '台風', '災害', '避難', '警報', '緊急',
            'earthquake', 'tsunami', 'typhoon', 'disaster', 'emergency'
        ]
        
        for title in titles:
            title_lower = title.lower()
            for keyword in disaster_keywords:
                if keyword.lower() in title_lower:
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