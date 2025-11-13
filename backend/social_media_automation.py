#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Social Media Automation Service
Handles automatic posting and commenting on multiple social media platforms
"""

import asyncio
import logging
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
import uuid
import aiohttp
import os

from social_media_config import (
    PlatformType, PostType, SocialMediaChannel,
    load_social_media_config, POST_TEMPLATES, AI_PROMPTS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RecurringJob:
    """In-memory recurring job definition for automatic posting/commenting"""
    id: str
    channel_ids: List[str]
    mode: Literal["self_post", "comment"]
    post_type: PostType
    frequency_minutes: int
    targets: Optional[List[str]] = None
    content: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: datetime = field(default_factory=lambda: datetime.now())

class SocialMediaAutomation:
    """Main social media automation service"""
    
    def __init__(self):
        self.config = load_social_media_config()
        self.channels: Dict[str, SocialMediaChannel] = {}
        self.ai_service = None
        self.is_running = False
        self.post_history: List[Dict] = []
        self.recurring_jobs: Dict[str, RecurringJob] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Initialize AI service
        self._init_ai_service()
        
        # Load channels
        self._load_channels()
        
        logger.info("✓ Social Media Automation Service initialized")

        # Start scheduler loop
        try:
            self.start_scheduler()
        except Exception as e:
            logger.warning(f"Failed to start scheduler: {e}")
    
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
        channels_data = self.config["channels"]
        
        for channel_id, config in channels_data.items():
            try:
                channel = SocialMediaChannel(
                    platform=PlatformType(config['platform']),
                    channel_id=config['channel_id'],
                    channel_name=config['channel_name'],
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
                logger.error(f"Error loading channel {channel_id}: {e}")
    
    async def post_emergency_alert(self, disaster_type: str, disaster_data: Dict, channel_ids: Optional[List[str]] = None) -> List[str]:
        """Post emergency alert to all active channels"""
        post_ids = []
        
        for channel_id, channel in self.channels.items():
            if not channel.is_active or not channel.auto_posting:
                continue
            
            if disaster_type not in channel.disaster_types:
                continue
            if channel_ids is not None and channel_id not in channel_ids:
                continue
            
            try:
                # Generate content
                content = await self._generate_content(channel, "emergency_alert", disaster_data)
                
                # Post to platform
                post_id = await self._post_to_platform(channel, content, PostType.EMERGENCY_ALERT)
                if post_id:
                    post_ids.append(post_id)
                    self._log_post(channel, content, post_id, "emergency_alert")
                    logger.info(f"✓ Posted emergency alert to {channel.channel_name}")
                
            except Exception as e:
                logger.error(f"Error posting emergency alert to {channel.channel_name}: {e}")
        
        return post_ids
    
    async def post_situation_update(self, situation_data: Dict, channel_ids: Optional[List[str]] = None) -> List[str]:
        """Post situation update to relevant channels"""
        post_ids = []
        
        for channel_id, channel in self.channels.items():
            if not channel.is_active or not channel.auto_posting:
                continue
            if channel_ids is not None and channel_id not in channel_ids:
                continue
            
            try:
                content = await self._generate_content(channel, "situation_update", situation_data)
                post_id = await self._post_to_platform(channel, content, PostType.SITUATION_UPDATE)
                if post_id:
                    post_ids.append(post_id)
                    self._log_post(channel, content, post_id, "situation_update")
                    logger.info(f"✓ Posted situation update to {channel.channel_name}")
                
            except Exception as e:
                logger.error(f"Error posting situation update to {channel.channel_name}: {e}")
        
        return post_ids
    
    async def post_evacuation_order(self, evacuation_data: Dict, channel_ids: Optional[List[str]] = None) -> List[str]:
        """Post evacuation order to relevant channels"""
        post_ids = []
        
        for channel_id, channel in self.channels.items():
            if not channel.is_active or not channel.auto_posting:
                continue
            if channel_ids is not None and channel_id not in channel_ids:
                continue
            
            try:
                content = await self._generate_content(channel, "evacuation_order", evacuation_data)
                post_id = await self._post_to_platform(channel, content, PostType.EVACUATION_ORDER)
                if post_id:
                    post_ids.append(post_id)
                    self._log_post(channel, content, post_id, "evacuation_order")
                    logger.info(f"✓ Posted evacuation order to {channel.channel_name}")
                
            except Exception as e:
                logger.error(f"Error posting evacuation order to {channel.channel_name}: {e}")
        
        return post_ids
    
    async def _generate_content(self, channel: SocialMediaChannel, content_type: str, data: Dict) -> str:
        """Generate content using AI or templates"""
        
        # Try AI generation first
        if self.ai_service and channel.language in AI_PROMPTS.get(content_type, {}):
            try:
                ai_content = await self._generate_ai_content(channel, content_type, data)
                if ai_content:
                    return ai_content
            except Exception as e:
                logger.warning(f"AI content generation failed: {e}")
        
        # Fallback to template
        template_key = f"{content_type}_{channel.language}"
        template = POST_TEMPLATES.get(template_key)
        
        if template:
            try:
                return template["template"].format(**data)
            except KeyError as e:
                logger.warning(f"Missing template variable {e}")
        
        # Final fallback
        return self._generate_fallback_content(content_type, data, channel.language)
    
    async def _generate_ai_content(self, channel: SocialMediaChannel, content_type: str, data: Dict) -> Optional[str]:
        """Generate content using AI"""
        
        if not self.ai_service:
            return None
        
        try:
            prompt_template = AI_PROMPTS.get(content_type, {}).get(channel.language)
            if not prompt_template:
                return None
            
            prompt = prompt_template.format(**data)
            
            response = await asyncio.to_thread(
                self.ai_service.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"AI content generation failed: {e}")
            return None
    
    def _generate_fallback_content(self, content_type: str, data: Dict, language: str) -> str:
        """Generate fallback content when AI and templates fail"""
        
        if language == "ja":
            if content_type in ("emergency", "emergency_alert"):
                disaster_type = data.get('type', 'unknown')
                if disaster_type == "earthquake":
                    return f"🚨 地震発生 🚨\n震源地: {data.get('location', '不明')}\nマグニチュード: {data.get('magnitude', '不明')}\n\n⚠️ 安全な場所に避難してください\n#地震 #緊急"
                elif disaster_type == "tsunami":
                    return f"🌊 津波警報 🌊\n対象地域: {data.get('location', '不明')}\n予想波高: {data.get('wave_height', '不明')}m\n\n🚨 沿岸部の方は高台に避難\n#津波 #警報"
                else:
                    return f"🚨 災害発生 🚨\n種類: {disaster_type}\n地域: {data.get('location', '不明')}\n\n⚠️ 安全を確保してください\n#災害 #緊急"
            elif content_type in ("situation", "situation_update"):
                return f"📊 状況更新 📊\n現在の状況: {data.get('current_situation', '確認中')}\n影響範囲: {data.get('affected_areas', '確認中')}\n\n最新情報は公式発表をご確認ください\n#災害情報"
            elif content_type in ("evacuation", "evacuation_order"):
                return f"🚨 避難指示 🚨\n対象地域: {data.get('area', '不明')}\n避難先: {data.get('destination', '高台')}\n\n📱 避難アプリでルート確認\n📞 家族に連絡\n#避難指示"
        else:
            if content_type in ("emergency", "emergency_alert"):
                disaster_type = data.get('type', 'unknown')
                if disaster_type == "earthquake":
                    return f"🚨 EARTHQUAKE ALERT 🚨\nLocation: {data.get('location', 'Unknown')}\nMagnitude: {data.get('magnitude', 'Unknown')}\n\n⚠️ Seek shelter immediately\n#Earthquake #Emergency"
                else:
                    return f"🚨 DISASTER ALERT 🚨\nType: {disaster_type}\nLocation: {data.get('location', 'Unknown')}\n\n⚠️ Ensure your safety\n#Disaster #Emergency"
            elif content_type in ("situation", "situation_update"):
                return f"📊 SITUATION UPDATE 📊\nCurrent situation: {data.get('current_situation', 'Under investigation')}\nAffected areas: {data.get('affected_areas', 'Under investigation')}\n\nPlease check official announcements for latest information\n#DisasterInfo"
            elif content_type in ("evacuation", "evacuation_order"):
                return f"🚨 EVACUATION ORDER 🚨\nTarget area: {data.get('area', 'Unknown')}\nDestination: {data.get('destination', 'High ground')}\n\n📱 Check evacuation app for routes\n📞 Contact family\n#Evacuation"
        
        return f"Emergency alert: {data.get('message', 'Please check official sources for information')}"
    
    async def _post_to_platform(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
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
            elif channel.platform == PlatformType.TWITTER:
                return await self._post_to_twitter(channel, content, post_type)
            else:
                logger.warning(f"Platform {channel.platform.value} not implemented")
                return None
                
        except Exception as e:
            logger.error(f"Error posting to {channel.platform.value}: {e}")
            return None
    
    async def _post_to_line(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to LINE"""
        try:
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
            if not channel.api_key:
                logger.error("YouTube API key required for live commenting")
                return None
            
            # YouTube Data API v3 implementation would go here
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
            logger.info(f"Would post to TikTok: {content[:50]}...")
            return f"tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to TikTok: {e}")
            return None
    
    async def _post_to_yahoo(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to Yahoo!"""
        try:
            # Yahoo! API implementation would go here
            logger.info(f"Would post to Yahoo!: {content[:50]}...")
            return f"yahoo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to Yahoo!: {e}")
            return None
    
    async def _post_to_twitter(self, channel: SocialMediaChannel, content: str, post_type: PostType) -> Optional[str]:
        """Post to Twitter/X"""
        try:
            # Twitter API v2 implementation would go here
            logger.info(f"Would post to Twitter: {content[:50]}...")
            return f"twitter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            logger.error(f"Error posting to Twitter: {e}")
            return None
    
    def _log_post(self, channel: SocialMediaChannel, content: str, post_id: str, post_type: str):
        """Log a successful post"""
        self.post_history.append({
            'timestamp': datetime.now().isoformat(),
            'channel_id': channel.channel_id,
            'channel_name': channel.channel_name,
            'platform': channel.platform.value,
            'post_type': post_type,
            'post_id': post_id,
            'content_preview': content[:100] + "..." if len(content) > 100 else content
        })
        
        # Keep only last 1000 posts in history
        if len(self.post_history) > 1000:
            self.post_history = self.post_history[-1000:]
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'total_channels': len(self.channels),
            'active_channels': len([c for c in self.channels.values() if c.is_active]),
            'platforms': {
                platform.value: len([c for c in self.channels.values() if c.platform == platform])
                for platform in PlatformType
            },
            'recent_posts': len([p for p in self.post_history if datetime.fromisoformat(p['timestamp']) > datetime.now() - timedelta(hours=1)]),
            'total_posts_today': len([p for p in self.post_history if datetime.fromisoformat(p['timestamp']) > datetime.now() - timedelta(days=1)]),
            'ai_service_available': self.ai_service is not None,
            'recurring_jobs': len([j for j in self.recurring_jobs.values() if j.enabled])
        }
    
    async def get_post_history(self, hours: int = 24) -> List[Dict]:
        """Get post history for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            post for post in self.post_history
            if datetime.fromisoformat(post['timestamp']) > cutoff_time
        ]

    # ========== Scheduler and Recurring Jobs ==========
    def start_scheduler(self):
        """Start background scheduler loop if not already running"""
        if self._scheduler_task and not self._scheduler_task.done():
            return
        self.is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("✓ Social media recurring scheduler started")

    def stop_scheduler(self):
        """Stop background scheduler loop"""
        self.is_running = False
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            self._scheduler_task = None

    async def _scheduler_loop(self):
        """Periodically execute due recurring jobs"""
        try:
            while self.is_running:
                now = datetime.now()
                due_jobs = [j for j in self.recurring_jobs.values() if j.enabled and j.next_run <= now]
                for job in due_jobs:
                    try:
                        await self._run_recurring_job(job)
                        job.last_run = now
                        job.next_run = now + timedelta(minutes=max(1, job.frequency_minutes))
                    except Exception as e:
                        logger.error(f"Error running recurring job {job.id}: {e}")
                        job.next_run = now + timedelta(minutes=max(1, job.frequency_minutes))
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Recurring scheduler task cancelled")

    async def _run_recurring_job(self, job: RecurringJob):
        """Execute a single recurring job across its configured channels"""
        logger.info(f"Running recurring job {job.id} for channels={job.channel_ids} type={job.post_type.value}")

        if job.mode == "self_post":
            if job.post_type == PostType.EMERGENCY_ALERT:
                disaster_type = job.content.get("disaster_type", job.content.get("type", "unknown"))
                await self.post_emergency_alert(disaster_type, job.content, channel_ids=job.channel_ids)
            elif job.post_type == PostType.SITUATION_UPDATE:
                await self.post_situation_update(job.content, channel_ids=job.channel_ids)
            elif job.post_type == PostType.EVACUATION_ORDER:
                await self.post_evacuation_order(job.content, channel_ids=job.channel_ids)
            else:
                for channel_id in job.channel_ids:
                    channel = self.channels.get(channel_id)
                    if not channel:
                        continue
                    content = await self._generate_content(channel, job.post_type.value, job.content)
                    await self._post_to_platform(channel, content, job.post_type)
        else:
            for channel_id in job.channel_ids:
                channel = self.channels.get(channel_id)
                if not channel:
                    continue
                content = await self._generate_content(channel, job.post_type.value, job.content)
                await self._comment_on_platform(channel, content, job.targets or [])

    async def _comment_on_platform(self, channel: SocialMediaChannel, content: str, targets: List[str]) -> Optional[str]:
        """Post a comment on external targets depending on platform. Returns comment id when available."""
        try:
            if channel.platform == PlatformType.YOUTUBE_LIVE:
                target_info = targets[0] if targets else "unknown_target"
                logger.info(f"Would comment to YouTube Live target={target_info}: {content[:60]}...")
                return f"yt_comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            elif channel.platform == PlatformType.LINE:
                if not targets:
                    return None
                headers = {
                    'Authorization': f'Bearer {channel.access_token}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'to': targets[0],
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
                            logger.error(f"LINE API error (comment): {response.status}")
                            return None
            elif channel.platform == PlatformType.TIKTOK:
                logger.info(f"Would comment to TikTok targets={targets}: {content[:60]}...")
                return f"tiktok_comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            elif channel.platform == PlatformType.YAHOO:
                logger.info(f"Would comment to Yahoo! targets={targets}: {content[:60]}...")
                return f"yahoo_comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except Exception as e:
            logger.error(f"Error commenting on {channel.platform.value}: {e}")
            return None

    async def create_recurring_job(self,
                                   channel_ids: List[str],
                                   mode: Literal["self_post", "comment"],
                                   post_type: PostType,
                                   frequency_minutes: int,
                                   targets: Optional[List[str]] = None,
                                   content: Optional[Dict[str, Any]] = None,
                                   enabled: bool = True) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = RecurringJob(
            id=job_id,
            channel_ids=channel_ids,
            mode=mode,
            post_type=post_type,
            frequency_minutes=max(1, int(frequency_minutes)),
            targets=targets or [],
            content=content or {},
            enabled=enabled,
        )
        self.recurring_jobs[job_id] = job
        logger.info(f"✓ Created recurring job {job_id} for channels={channel_ids}")
        return job_id

    async def list_recurring_jobs(self) -> List[Dict[str, Any]]:
        def serialize(job: RecurringJob) -> Dict[str, Any]:
            return {
                "id": job.id,
                "channel_ids": job.channel_ids,
                "mode": job.mode,
                "post_type": job.post_type.value,
                "frequency_minutes": job.frequency_minutes,
                "targets": job.targets,
                "content": job.content,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
            }
        return [serialize(job) for job in self.recurring_jobs.values()]

    async def update_recurring_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        job = self.recurring_jobs.get(job_id)
        if not job:
            return False
        if "channel_ids" in updates:
            job.channel_ids = list(updates["channel_ids"]) or job.channel_ids
        if "mode" in updates:
            job.mode = updates["mode"]  # type: ignore
        if "post_type" in updates:
            pt = updates["post_type"]
            job.post_type = pt if isinstance(pt, PostType) else PostType(pt)
        if "frequency_minutes" in updates:
            job.frequency_minutes = max(1, int(updates["frequency_minutes"]))
        if "targets" in updates:
            job.targets = list(updates["targets"]) if updates["targets"] is not None else []
        if "content" in updates:
            job.content = dict(updates["content"]) if updates["content"] is not None else {}
        if "enabled" in updates:
            job.enabled = bool(updates["enabled"])
        if updates.get("reset_next_run"):
            job.next_run = datetime.now()
        return True

    async def delete_recurring_job(self, job_id: str) -> bool:
        return self.recurring_jobs.pop(job_id, None) is not None

# Global instance
social_media_automation = None

async def init_social_media_automation():
    """Initialize the social media automation service"""
    global social_media_automation
    social_media_automation = SocialMediaAutomation()
    return social_media_automation 