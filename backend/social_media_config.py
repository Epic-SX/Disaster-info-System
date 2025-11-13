#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Social Media Configuration
Configuration settings for social media automation
"""

import os
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

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
    api_key: str = None
    api_secret: str = None
    webhook_url: str = None
    is_active: bool = True
    auto_posting: bool = True
    auto_commenting: bool = True
    posting_frequency: int = 30  # minutes
    commenting_frequency: int = 15  # minutes
    max_posts_per_day: int = 50
    max_comments_per_day: int = 100
    disaster_types: List[str] = None
    language: str = "ja"
    timezone: str = "Asia/Tokyo"

# Default social media channels configuration
DEFAULT_CHANNELS = {
    "line_disaster_info": {
        "platform": "line",
        "channel_id": "your_line_channel_id",
        "channel_name": "Disaster Information LINE",
        "access_token": "your_line_access_token",
        "auto_posting": True,
        "auto_commenting": True,
        "posting_frequency": 30,
        "disaster_types": ["earthquake", "tsunami", "typhoon"],
        "language": "ja"
    },
    "youtube_live_emergency": {
        "platform": "youtube_live",
        "channel_id": "your_youtube_channel_id",
        "channel_name": "Emergency Broadcast YouTube",
        "access_token": "your_youtube_access_token",
        "api_key": "your_youtube_api_key",
        "auto_posting": True,
        "auto_commenting": True,
        "posting_frequency": 15,
        "disaster_types": ["earthquake", "tsunami"],
        "language": "ja"
    },
    "tiktok_disaster_updates": {
        "platform": "tiktok",
        "channel_id": "your_tiktok_channel_id",
        "channel_name": "Disaster Updates TikTok",
        "access_token": "your_tiktok_access_token",
        "auto_posting": True,
        "auto_commenting": False,
        "posting_frequency": 60,
        "disaster_types": ["earthquake", "tsunami", "typhoon"],
        "language": "ja"
    },
    "yahoo_emergency": {
        "platform": "yahoo",
        "channel_id": "your_yahoo_channel_id",
        "channel_name": "Emergency Yahoo!",
        "access_token": "your_yahoo_access_token",
        "auto_posting": True,
        "auto_commenting": True,
        "posting_frequency": 45,
        "disaster_types": ["earthquake", "tsunami", "typhoon"],
        "language": "ja"
    }
}

# Post templates for different platforms and content types
POST_TEMPLATES = {
    "emergency_earthquake_ja": {
        "platform": "line",
        "post_type": "emergency_alert",
        "template": "🚨 緊急地震速報 🚨\n\n震源地: {location}\nマグニチュード: {magnitude}\n最大震度: {intensity}\n\n⚠️ 安全な場所に避難してください\n📞 緊急時は119番に連絡\n\n#地震 #緊急速報 #避難",
        "variables": ["location", "magnitude", "intensity"],
        "max_length": 200,
        "language": "ja"
    },
    "emergency_tsunami_ja": {
        "platform": "line",
        "post_type": "emergency_alert",
        "template": "🌊 津波警報発令 🌊\n\n対象地域: {location}\n予想波高: {wave_height}m\n到達予想時刻: {arrival_time}\n\n🚨 沿岸部の方は高台に避難してください\n\n#津波 #警報 #避難",
        "variables": ["location", "wave_height", "arrival_time"],
        "max_length": 200,
        "language": "ja"
    },
    "situation_update_ja": {
        "platform": "youtube_live",
        "post_type": "situation_update",
        "template": "📊 災害状況更新 📊\n\n現在の状況: {current_situation}\n影響範囲: {affected_areas}\n避難所: {shelters}\n\n最新情報は公式発表をご確認ください\n\n#災害情報 #状況更新",
        "variables": ["current_situation", "affected_areas", "shelters"],
        "max_length": 300,
        "language": "ja"
    },
    "evacuation_order_ja": {
        "platform": "tiktok",
        "post_type": "evacuation_order",
        "template": "🚨 避難指示発令 🚨\n\n対象地域: {area}\n避難先: {destination}\n緊急度: {urgency_level}\n\n📱 避難アプリでルート確認\n📞 家族に連絡\n\n#避難指示 #安全第一",
        "variables": ["area", "destination", "urgency_level"],
        "max_length": 250,
        "language": "ja"
    },
    "safety_tips_ja": {
        "platform": "yahoo",
        "post_type": "safety_tips",
        "template": "💡 防災の豆知識 💡\n\n{tip_title}\n\n{tip_content}\n\n備えあれば憂いなし！\n\n#防災 #安全 #豆知識",
        "variables": ["tip_title", "tip_content"],
        "max_length": 280,
        "language": "ja"
    },
    "emergency_earthquake_en": {
        "platform": "twitter",
        "post_type": "emergency_alert",
        "template": "🚨 EMERGENCY EARTHQUAKE ALERT 🚨\n\nLocation: {location}\nMagnitude: {magnitude}\nIntensity: {intensity}\n\n⚠️ Seek shelter immediately\n📞 Call 119 for emergencies\n\n#Earthquake #Emergency #Safety",
        "variables": ["location", "magnitude", "intensity"],
        "max_length": 280,
        "language": "en"
    }
}

# AI content generation prompts
AI_PROMPTS = {
    "emergency_alert": {
        "ja": "災害情報システム用の緊急アラート投稿を生成してください。\n\nデータ: {data}\n\n要件:\n- 280文字以内\n- 適切な絵文字とフォーマット\n- 分かりやすく情報提供\n- 関連ハッシュタグを含む\n- 緊急性を強調\n\n投稿を生成してください:",
        "en": "Generate an emergency alert post for a disaster information system.\n\nData: {data}\n\nRequirements:\n- Within 280 characters\n- Use appropriate emojis and formatting\n- Make it clear and informative\n- Include relevant hashtags\n- Emphasize urgency\n\nGenerate the post:"
    },
    "situation_update": {
        "ja": "災害状況の更新投稿を生成してください。\n\n現在の状況: {current_situation}\n影響範囲: {affected_areas}\n\n要件:\n- 300文字以内\n- 正確で最新の情報\n- 冷静で落ち着いたトーン\n- 実用的なアドバイスを含む\n\n投稿を生成してください:",
        "en": "Generate a situation update post for disaster information.\n\nCurrent situation: {current_situation}\nAffected areas: {affected_areas}\n\nRequirements:\n- Within 300 characters\n- Accurate and current information\n- Calm and composed tone\n- Include practical advice\n\nGenerate the post:"
    },
    "evacuation_order": {
        "ja": "避難指示の投稿を生成してください。\n\n対象地域: {area}\n避難先: {destination}\n緊急度: {urgency_level}\n\n要件:\n- 250文字以内\n- 明確で具体的な指示\n- 緊急性を適切に表現\n- 安全な避難方法のアドバイス\n\n投稿を生成してください:",
        "en": "Generate an evacuation order post.\n\nTarget area: {area}\nEvacuation destination: {destination}\nUrgency level: {urgency_level}\n\nRequirements:\n- Within 250 characters\n- Clear and specific instructions\n- Appropriate urgency expression\n- Safe evacuation advice\n\nGenerate the post:"
    }
}

# Posting schedules
POSTING_SCHEDULES = {
    "emergency": {
        "frequency": "immediate",
        "retry_interval": 5,  # minutes
        "max_retries": 3
    },
    "high_priority": {
        "frequency": 5,  # minutes
        "retry_interval": 10,
        "max_retries": 2
    },
    "normal": {
        "frequency": 30,  # minutes
        "retry_interval": 15,
        "max_retries": 1
    },
    "low_priority": {
        "frequency": 60,  # minutes
        "retry_interval": 30,
        "max_retries": 1
    }
}

# Disaster type configurations
DISASTER_CONFIGS = {
    "earthquake": {
        "emergency_threshold": 5.0,  # magnitude
        "immediate_posting": True,
        "platforms": ["line", "youtube_live", "twitter"],
        "content_type": "emergency_alert",
        "ai_enhancement": True
    },
    "tsunami": {
        "emergency_threshold": 1.0,  # wave height in meters
        "immediate_posting": True,
        "platforms": ["line", "youtube_live", "twitter"],
        "content_type": "emergency_alert",
        "ai_enhancement": True
    },
    "typhoon": {
        "emergency_threshold": 60,  # wind speed in km/h
        "immediate_posting": False,
        "platforms": ["line", "yahoo", "twitter"],
        "content_type": "situation_update",
        "ai_enhancement": True
    },
    "flood": {
        "emergency_threshold": "moderate",
        "immediate_posting": False,
        "platforms": ["line", "yahoo"],
        "content_type": "situation_update",
        "ai_enhancement": False
    }
}

def load_social_media_config():
    """Load social media configuration from environment or defaults"""
    config = {
        "channels": DEFAULT_CHANNELS,
        "templates": POST_TEMPLATES,
        "ai_prompts": AI_PROMPTS,
        "schedules": POSTING_SCHEDULES,
        "disaster_configs": DISASTER_CONFIGS
    }
    
    # Override with environment variables if available
    social_media_channels = os.getenv('SOCIAL_MEDIA_CHANNELS')
    if social_media_channels:
        try:
            import json
            config["channels"].update(json.loads(social_media_channels))
        except Exception as e:
            print(f"Error loading social media channels from environment: {e}")
    
    return config 