#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Social Media Automation Service
Provides automatic posting and commenting on multiple social media platforms
Supports LINE, YouTube LIVE, TikTok, and Yahoo! with AI-generated content
"""

import os
import asyncio
import logging
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import schedule
import time
from threading import Thread

# Load environment variables
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

class PlatformType(Enum):
    """Supported social media platforms"""
    LINE = "line"
    YOUTUBE_LIVE = "youtube_live"
    TIKTOK = "tiktok"
    YAHOO = "yahoo"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"

class PostType(Enum):
    """Types of social media posts"""
    EMERGENCY_ALERT = "emergency_alert"
    SITUATION_UPDATE = "situation_update"
    EVACUATION_ORDER = "evacuation_order"
    SAFETY_TIPS = "safety_tips"
    WEATHER_UPDATE = "weather_update"
    GENERAL_INFO = "general_info"

@dataclass
class SocialMediaChannel:
    """Configuration for a social media channel"""
    platform: PlatformType
    channel_id: str
    channel_name: str
    access_token: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    is_active: bool = True
    auto_posting: bool = True
    auto_commenting: bool = True
    posting_frequency: int = 30  # minutes
    commenting_frequency: int = 15  # minutes
    max_posts_per_day: int = 50
    max_comments_per_day: int = 100
    disaster_types: List[str] = field(default_factory=lambda: ["earthquake", "tsunami", "typhoon"])
    language: str = "ja"
    timezone: str = "Asia/Tokyo"

@dataclass
class PostTemplate:
    """Template for AI-generated social media posts"""
    id: str
    platform: PlatformType
    post_type: PostType
    template: str
    variables: List[str] = field(default_factory=list)
    max_length: int = 280
    language: str = "ja"
    is_active: bool = True

@dataclass
class ScheduledPost:
    """Scheduled social media post"""
    id: str
    channel_id: str
    platform: PlatformType
    post_type: PostType
    content: str
    scheduled_time: datetime
    status: str = "pending"  # pending, posted, failed, cancelled
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict = field(default_factory=dict)

class SocialMediaAutomationService:
    """Comprehensive social media automation service"""
    
    def __init__(self):
        self.channels: Dict[str, SocialMediaChannel] = {}
        self.templates: Dict[str, PostTemplate] = {}
        self.scheduled_posts: List[ScheduledPost] = []
        self.disaster_data_cache: Dict = {}
        self.ai_service = None
        self.is_running = False
        
        # Initialize AI service for content generation
        self._init_ai_service()
        
        # Load channels and templates
        self._load_channels()
        self._load_templates()
        
        # Start automation scheduler
        self._start_scheduler()
    
    def _init_ai_service(self):
        """Initialize AI service for content generation"""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.ai_service = openai
                self.ai_service.api_key = api_key
                logger.info("✓ AI service initialized for content generation")
            else:
                logger.warning("⚠️ OpenAI API key not found - AI content generation disabled")
        except ImportError:
            logger.warning("⚠️ OpenAI library not available - AI content generation disabled")
    
    def _load_channels(self):
        """Load social media channels from configuration"""
        # Load from environment variables or config file
        channels_config = os.getenv('SOCIAL_MEDIA_CHANNELS', '{}')
        try:
            channels_data = json.loads(channels_config)
            for channel_id, config in channels_data.items():
                channel = SocialMediaChannel(
                    platform=PlatformType(config['platform']),
                    channel_id=channel_id,
                    channel_name=config.get('channel_name', channel_id),
                    access_token=config['access_token'],
                    api_key=config.get('api_key'),
                    api_secret=config.get('api_secret'),
                    webhook_url=config.get('webhook_url'),
                    is_active=config.get('is_active', True),
                    auto_posting=config.get('auto_posting', True),
                    auto_commenting=config.get('auto_commenting', True),
                    posting_frequency=config.get('posting_frequency', 30),
                    commenting_frequency=config.get('commenting_frequency', 15),
                    max_posts_per_day=config.get('max_posts_per_day', 50),
                    max_comments_per_day=config.get('max_comments_per_day', 100),
                    disaster_types=config.get('disaster_types', ["earthquake", "tsunami", "typhoon"]),
                    language=config.get('language', 'ja'),
                    timezone=config.get('timezone', 'Asia/Tokyo')
                )
                self.channels[channel_id] = channel
                logger.info(f"✓ Loaded channel: {channel.channel_name} ({channel.platform.value})")
        except Exception as e:
            logger.error(f"Error loading channels: {e}")
    
    def _load_templates(self):
        """Load post templates for different platforms and content types"""
        templates = [
            # Emergency Alerts
            PostTemplate(
                id="emergency_earthquake_ja",
                platform=PlatformType.LINE,
                post_type=PostType.EMERGENCY_ALERT,
                template="🚨 緊急地震速報 🚨\n\n震源地: {location}\nマグニチュード: {magnitude}\n最大震度: {intensity}\n\n⚠️ 安全な場所に避難してください\n📞 緊急時は119番に連絡\n\n#地震 #緊急速報 #避難",
                variables=["location", "magnitude", "intensity"],
                max_length=200,
                language="ja"
            ),
            PostTemplate(
                id="emergency_tsunami_ja",
                platform=PlatformType.LINE,
                post_type=PostType.EMERGENCY_ALERT,
                template="🌊 津波警報発令 🌊\n\n対象地域: {location}\n予想波高: {wave_height}m\n到達予想時刻: {arrival_time}\n\n🚨 沿岸部の方は高台に避難してください\n\n#津波 #警報 #避難",
                variables=["location", "wave_height", "arrival_time"],
                max_length=200,
                language="ja"
            )
        ]
        
        for template in templates:
            self.templates[template.id] = template
        
        logger.info(f"✓ Loaded {len(templates)} post templates")
    
    def _start_scheduler(self):
        """Start the automation scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start scheduler in background thread
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Schedule regular tasks
        schedule.every(5).minutes.do(self._check_for_disasters)
        schedule.every(10).minutes.do(self._process_scheduled_posts)
        schedule.every(15).minutes.do(self._generate_ai_content)
        
        logger.info("✓ Social media automation scheduler started")
    
    async def post_emergency_alert(self, disaster_type: str, disaster_data: Dict) -> List[str]:
        """Post emergency alert to all active channels"""
        
        post_ids = []
        
        for channel_id, channel in self.channels.items():
            if not channel.is_active or not channel.auto_posting:
                continue
            
            if disaster_type not in channel.disaster_types:
                continue
            
            try:
                # Generate content using AI
                content = await self._generate_emergency_content(channel, disaster_type, disaster_data)
                
                # Post immediately for emergency alerts
                post_id = await self._post_to_platform(channel, content, PostType.EMERGENCY_ALERT)
                if post_id:
                    post_ids.append(post_id)
                    logger.info(f"✓ Posted emergency alert to {channel.channel_name}")
                
            except Exception as e:
                logger.error(f"Error posting emergency alert to {channel.channel_name}: {e}")
        
        return post_ids
    
    async def _generate_emergency_content(self, channel: SocialMediaChannel, 
                                       disaster_type: str, disaster_data: Dict) -> str:
        """Generate emergency content using AI or templates"""
        
        # Find appropriate template
        template_key = f"emergency_{disaster_type}_{channel.language}"
        template = self.templates.get(template_key)
        
        if not template:
            # Fallback to generic emergency template
            template = self.templates.get(f"emergency_earthquake_{channel.language}")
        
        if template and self.ai_service:
            # Use AI to enhance the template
            try:
                enhanced_content = await self._enhance_content_with_ai(template, disaster_data)
                return enhanced_content
            except Exception as e:
                logger.warning(f"AI enhancement failed, using template: {e}")
        
        # Use template with disaster data
        if template:
            try:
                return template.template.format(**disaster_data)
            except KeyError as e:
                logger.warning(f"Missing template variable {e}, using fallback")
        
        # Fallback content
        return self._generate_fallback_content(disaster_type, disaster_data, channel.language)
    
    async def _enhance_content_with_ai(self, template: PostTemplate, data: Dict) -> str:
        """Enhance content using AI"""
        
        if not self.ai_service:
            return template.template.format(**data)
        
        try:
            prompt = f"""
            Generate a social media post for a disaster information system.
            
            Template: {template.template}
            Data: {json.dumps(data, ensure_ascii=False)}
            
            Requirements:
            - Keep within {template.max_length} characters
            - Use appropriate emojis and formatting
            - Make it engaging and informative
            - Include relevant hashtags
            - Language: {template.language}
            
            Generate the enhanced post:
            """
            
            response = await asyncio.to_thread(
                self.ai_service.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            enhanced_content = response.choices[0].message.content.strip()
            return enhanced_content
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return template.template.format(**data)
    
    def _generate_fallback_content(self, disaster_type: str, data: Dict, language: str) -> str:
        """Generate fallback content when AI and templates fail"""
        
        if language == "ja":
            if disaster_type == "earthquake":
                return f"🚨 地震発生 🚨\n震源地: {data.get('location', '不明')}\nマグニチュード: {data.get('magnitude', '不明')}\n\n⚠️ 安全な場所に避難してください\n#地震 #緊急"
            elif disaster_type == "tsunami":
                return f"🌊 津波警報 🌊\n対象地域: {data.get('location', '不明')}\n予想波高: {data.get('wave_height', '不明')}m\n\n🚨 沿岸部の方は高台に避難\n#津波 #警報"
            else:
                return f"🚨 災害発生 🚨\n種類: {disaster_type}\n地域: {data.get('location', '不明')}\n\n⚠️ 安全を確保してください\n#災害 #緊急"
        else:
            if disaster_type == "earthquake":
                return f"🚨 EARTHQUAKE ALERT 🚨\nLocation: {data.get('location', 'Unknown')}\nMagnitude: {data.get('magnitude', 'Unknown')}\n\n⚠️ Seek shelter immediately\n#Earthquake #Emergency"
            else:
                return f"🚨 DISASTER ALERT 🚨\nType: {disaster_type}\nLocation: {data.get('location', 'Unknown')}\n\n⚠️ Ensure your safety\n#Disaster #Emergency"
    
    async def _post_to_platform(self, channel: SocialMediaChannel, content: str, 
                               post_type: PostType) -> Optional[str]:
        """Post content to specific platform"""
        
        try:
            if channel.platform == PlatformType.LINE:
                return await self._post_to_line(channel, content, post_type)
            elif channel.platform == PlatformType.YOUTUBE_LIVE:
                return await self._post_to_youtube_live(channel, content, post_type)
            elif channel.platform == PlatformType.TIKTOK:
                return await self._post_to_tiktok(channel, content, post_type)
            elif channel.platform == PlatformType.YAHOO:
                return await self._post_to_yahoo(channel, content, post_type)
            else:
                logger.warning(f"Platform {channel.platform.value} not implemented")
                return None
                
        except Exception as e:
            logger.error(f"Error posting to {channel.platform.value}: {e}")
            return None
    
    async def _post_to_line(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to LINE"""
        try:
            # LINE Messaging API implementation
            headers = {
                'Authorization': f'Bearer {channel.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'to': channel.channel_id,
                'messages': [{
                    'type': 'text',
                    'text': content
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.line.me/v2/bot/message/push',
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('messageId')
                    else:
                        logger.error(f"LINE API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error posting to LINE: {e}")
            return None
    
    async def _post_to_youtube_live(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post comment to YouTube Live"""
        try:
            # YouTube Data API v3 implementation
            if not channel.api_key:
                logger.error("YouTube API key required for live commenting")
                return None
            
            # This would require YouTube Data API v3 setup
            # For now, return a mock ID
            logger.info(f"Would post to YouTube Live: {content[:50]}...")
            return f"yt_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to YouTube Live: {e}")
            return None
    
    async def _post_to_tiktok(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to TikTok"""
        try:
            # TikTok API implementation would go here
            # For now, return a mock ID
            logger.info(f"Would post to TikTok: {content[:50]}...")
            return f"tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to TikTok: {e}")
            return None
    
    async def _post_to_yahoo(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to Yahoo!"""
        try:
            # Yahoo! API implementation would go here
            # For now, return a mock ID
            logger.info(f"Would post to Yahoo!: {content[:50]}...")
            return f"yahoo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to Yahoo!: {e}")
            return None
    
    async def get_channel_status(self) -> Dict[str, Any]:
        """Get status of all channels"""
        status = {
            'total_channels': len(self.channels),
            'active_channels': len([c for c in self.channels.values() if c.is_active]),
            'platforms': {},
            'scheduled_posts': len([p for p in self.scheduled_posts if p.status == "pending"]),
            'recent_posts': len([p for p in self.scheduled_posts if p.status == "posted" and p.scheduled_time > datetime.now() - timedelta(hours=1)])
        }
        
        for platform in PlatformType:
            platform_channels = [c for c in self.channels.values() if c.platform == platform]
            status['platforms'][platform.value] = {
                'total': len(platform_channels),
                'active': len([c for c in platform_channels if c.is_active])
            }
        
        return status
    
    async def update_disaster_data(self, disaster_data: Dict):
        """Update disaster data cache and trigger relevant posts"""
        self.disaster_data_cache.update(disaster_data)
        
        # Check if this is an emergency that requires immediate posting
        if disaster_data.get('emergency_level') in ['high', 'critical']:
            await self.post_emergency_alert(
                disaster_data.get('type', 'unknown'),
                disaster_data
            )
    
    def _check_for_disasters(self):
        """Check for new disasters and schedule posts"""
        # This would integrate with your disaster data sources
        pass
    
    def _process_scheduled_posts(self):
        """Process scheduled posts"""
        # Implementation for processing scheduled posts
        pass
    
    def _generate_ai_content(self):
        """Generate AI content for scheduled posts"""
        # Implementation for AI content generation
        pass

# Global instance
social_media_service = None

async def init_social_media_service():
    """Initialize the social media automation service"""
    global social_media_service
    social_media_service = SocialMediaAutomationService()
    return social_media_service 