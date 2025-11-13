#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Disaster Information System Backend API
Provides REST APIs for disaster data, YouTube chat integration, and social media automation.
"""

import os
import sys
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

# Load environment variables from .env file
def load_env_file():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env_file()

# Now import the rest of the modules
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import uvicorn

import json # Added for json.loads
import httpx

from fastapi.responses import JSONResponse, Response

from youtube_chat_service import YouTubeChatAnalyzer
from youtube_search_service import YouTubeSearchService, YouTubeVideo, YouTubeSearchResult
from disaster_api_service import DisasterAPIService, EarthquakeInfo, TsunamiInfo, DisasterAlert as DisasterAlertNew
from weather_service import get_current_wind_data
from jma_wind_service import get_wind_service
from youtube_live_streaming import get_streamer, YouTubeLiveStreamer, OBSStreamingConfig
from ai_commentary_service import get_commentary_service, AICommentaryService, CommentaryBroadcaster
from p2p_earthquake_service import (
    P2PEarthquakeService, P2PAPIConfig, InformationCode,
    JMAQuake, JMATsunami, EEW, EEWDetection, Userquake, UserquakeEvaluation,
    scale_int_to_string, parse_p2p_time
)
from social_media_automation import init_social_media_automation, social_media_automation
from social_media_config import PostType
from amedas_scheduler import get_scheduler, AMeDASScheduler


class Settings(BaseSettings):
    """Application settings from environment variables"""
    debug: bool = True
    port: int = 8000
    host: str = "0.0.0.0"  # Changed from localhost to bind to all interfaces
    log_level: str = "INFO"
    
    # API URLs
    jma_api_base_url: str = "https://www.jma.go.jp/bosai/forecast/data/forecast/"
    usgs_earthquake_api: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    nhk_news_api: str = "https://www3.nhk.or.jp/news/json16/"
    
    # Additional Disaster APIs
    p2p_earthquake_api: str = "https://api.p2pquake.net/v2"
    j_shis_api_base: str = "https://www.j-shis.bosai.go.jp/map"
    iij_earthquake_websocket: str = "wss://ws-api.iij.jp/v1/earthquake"
    
    # SerpApi Configuration
    serpapi_api_key: str = ""
    serpapi_base_url: str = "https://serpapi.com/search.json"
    
    # Weather API Configuration
    openweather_api_key: str = ""
    
    # WebSocket settings
    ws_host: str = "localhost"
    ws_port: int = 8001
    
    # Database settings
    database_url: str = "sqlite:///disaster_chat.db"
    
    # Chat settings
    max_chat_history: int = 1000
    sentiment_threshold: float = 0.7
    auto_response_cooldown: int = 30
    
    # API Keys
    openai_api_key: str = ""
    youtube_api_key: str = ""
    youtube_channel_id: str = ""
    youtube_live_chat_id: str = ""
    
    # AI settings
    ai_model: str = "gpt-3.5-turbo"
    max_tokens: int = 150
    temperature: float = 0.7
    
    # Alert thresholds
    earthquake_magnitude_threshold: float = 5.0
    tsunami_height_threshold: float = 1.0
    wind_speed_threshold: int = 60
    
    # Keywords
    disaster_keywords: str = "地震,津波,台風,豪雨,洪水,土砂災害,火災,避難,緊急,警報,earthquake,tsunami,typhoon,flood,emergency"
    product_keywords: str = "防災グッズ,非常食,懐中電灯,ラジオ,応急手当,emergency kit,flashlight,radio,first aid"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow case-insensitive matching
        extra = "allow"  # Allow extra fields for development flexibility


# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Use INFO initially, will be updated after settings load
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables
settings = Settings()

# Update logging level based on settings
logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

def log_settings():
    """Log current settings for debugging"""
    logger.info("=== Environment Settings Loaded ===")
    logger.info(f"DEBUG: {settings.debug}")
    logger.info(f"PORT: {settings.port}")
    logger.info(f"HOST: {settings.host}")
    logger.info(f"LOG_LEVEL: {settings.log_level}")
    logger.info(f"DATABASE_URL: {settings.database_url}")
    logger.info(f"OPENAI_API_KEY: {'***' if settings.openai_api_key else 'NOT SET'}")
    logger.info(f"YOUTUBE_API_KEY: {'***' if settings.youtube_api_key else 'NOT SET'}")
    logger.info(f"SERPAPI_API_KEY: {'***' if settings.serpapi_api_key else 'NOT SET'}")
    logger.info(f"EARTHQUAKE_MAGNITUDE_THRESHOLD: {settings.earthquake_magnitude_threshold}")
    logger.info(f"TSUNAMI_HEIGHT_THRESHOLD: {settings.tsunami_height_threshold}")
    logger.info(f"WIND_SPEED_THRESHOLD: {settings.wind_speed_threshold}")
    logger.info("=====================================")

# Log the loaded settings
log_settings()

chat_analyzer: Optional[YouTubeChatAnalyzer] = None
youtube_search_service: Optional[YouTubeSearchService] = None
disaster_api_service: Optional[DisasterAPIService] = None
p2p_earthquake_service: Optional[P2PEarthquakeService] = None
amedas_scheduler: Optional[AMeDASScheduler] = None
connected_websockets: List[WebSocket] = []

# Add missing global variables
chat_messages: List[dict] = []
active_connections: List[WebSocket] = []

# Global background task for periodic updates
periodic_update_task: Optional[asyncio.Task] = None

# Background task for sending periodic updates to all connected clients
async def global_periodic_updates():
    """Global background task for sending periodic updates to all WebSocket clients"""
    logger.info("Starting global periodic updates task")
    
    while True:
        try:
            if not connected_websockets:
                await asyncio.sleep(5)  # Wait 5 seconds if no connections
                continue
            
            # Send periodic analytics updates
            analytics_data = {
                "type": "analytics_update",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "total_messages": len(chat_messages),
                    "active_connections": len(connected_websockets),
                    "uptime": datetime.now().isoformat()
                }
            }
            await broadcast_to_websockets(analytics_data)
            
            # Send ping to keep connections alive
            ping_data = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }
            await broadcast_to_websockets(ping_data)
            
            # Wind data updates are now served from AMeDAS database (updated hourly)
            # Real-time API calls have been disabled to use scraped data instead
            # Wind data is available via REST API endpoints and initial WebSocket connection
            
            # Send news updates
            try:
                news_data = await fetch_real_time_news()
                news_update = {
                    "type": "news_update",
                    "news": [article.dict() for article in news_data],
                    "timestamp": datetime.now().isoformat()
                }
                await broadcast_to_websockets(news_update)
                logger.debug(f"Sent news update with {len(news_data)} articles")
            except Exception as e:
                logger.error(f"Error sending news updates: {e}")
            
            # Send camera feeds updates
            try:
                camera_data = await fetch_real_time_camera_feeds()
                camera_update = {
                    "type": "camera_feeds_update",
                    "camera_feeds": [feed.dict() for feed in camera_data],
                    "timestamp": datetime.now().isoformat()
                }
                await broadcast_to_websockets(camera_update)
                logger.debug(f"Sent camera feeds update with {len(camera_data)} feeds")
            except Exception as e:
                logger.error(f"Error sending camera feeds updates: {e}")
            
            # Send earthquake data updates
            try:
                # Try to get real earthquake data first
                earthquake_data = []
                if disaster_api_service:
                    try:
                        real_earthquakes = await disaster_api_service.get_comprehensive_earthquake_data()
                        if real_earthquakes:
                            # Convert to format expected by frontend
                            earthquake_data = [
                                {
                                    "id": eq.id,
                                    "time": eq.timestamp.isoformat(),
                                    "location": eq.location,
                                    "magnitude": eq.magnitude,
                                    "depth": eq.depth,
                                    "latitude": eq.latitude,
                                    "longitude": eq.longitude,
                                    "intensity": eq.intensity,
                                    "tsunami": eq.tsunami_warning
                                }
                                for eq in real_earthquakes[-10:]  # Latest 10 earthquakes
                            ]
                            source = "real_api"
                    except Exception as e:
                        logger.debug(f"Real earthquake API failed: {e}")
                        earthquake_data = []
                
                # Generate mock data if no real data available
                if not earthquake_data:
                    earthquake_data = _generate_mock_earthquake_data()
                    source = "mock_data"
                else:
                    source = "real_api"
                
                earthquake_update = {
                    "type": "earthquake_data_update",
                    "earthquakes": earthquake_data,
                    "timestamp": datetime.now().isoformat(),
                    "source": source
                }
                await broadcast_to_websockets(earthquake_update)
                logger.debug(f"Sent earthquake data update with {len(earthquake_data)} earthquakes (source: {source})")
                
            except Exception as e:
                logger.error(f"Error sending earthquake data updates: {e}")
            
            await asyncio.sleep(10)  # Send updates every 10 seconds
            
        except asyncio.CancelledError:
            logger.info("Periodic updates task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in global periodic updates: {e}")
            await asyncio.sleep(10)  # Continue after error


# Pydantic models for API responses
class ChatMessage(BaseModel):
    """Chat message model for API responses"""
    id: str
    message_id: str
    author: str
    message: str
    timestamp: str
    sentiment_score: float
    category: str
    platform: str


class DisasterAlert(BaseModel):
    id: str
    type: str
    severity: str
    location: str
    message: str
    timestamp: datetime
    coordinates: Optional[dict] = None


class EarthquakeData(BaseModel):
    magnitude: float
    location: str
    depth: float
    timestamp: datetime
    coordinates: dict
    intensity: Optional[str] = None


class NewsArticle(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    published_at: datetime
    category: str
    source: str
    time_ago: Optional[str] = None  # Human readable time like "2時間前"


class CameraFeed(BaseModel):
    id: str
    name: str
    status: str  # "online", "offline", "maintenance"
    location: str
    stream_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    last_updated: datetime
    coordinates: Optional[dict] = None  # For map display


class ChatAnalytics(BaseModel):
    total_messages: int
    disaster_mentions: int
    product_mentions: int
    sentiment_score: float
    top_keywords: List[str]
    active_users: int


class AutoResponse(BaseModel):
    """Auto response model for API responses"""
    id: int
    trigger_keywords: str
    response_text: str
    response_type: str
    used_count: int
    last_used_at: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global chat_analyzer, youtube_search_service, disaster_api_service, p2p_earthquake_service, amedas_scheduler, periodic_update_task
    
    # Startup
    logger.info("Starting Disaster Information System backend...")
    
    # Initialize YouTube search service
    try:
        youtube_search_service = YouTubeSearchService()
        logger.info("✓ YouTube search service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize YouTube search service: {e}")
        youtube_search_service = None
    
    # Initialize disaster API service
    try:
        disaster_api_service = DisasterAPIService()
        logger.info("✓ Disaster API service initialized successfully")
        
        # Note: IIJ WebSocket requires authentication - disabled for now
        # The system will use HTTP polling as fallback
        # asyncio.create_task(disaster_api_service.start_realtime_monitoring())
        logger.info("✓ Disaster API service initialized (HTTP mode)")
    except Exception as e:
        logger.error(f"Failed to initialize disaster API service: {e}")
        disaster_api_service = None
    
    # Initialize P2P earthquake service
    try:
        # Use production API (not sandbox) and enable WebSocket for real-time data
        p2p_config = P2PAPIConfig(
            use_sandbox=False,  # Use production API for real earthquake data
            enable_websocket=True,  # Enable WebSocket for real-time monitoring
            websocket_reconnect_interval=30,
            api_timeout=10,
            rate_limit_delay=1.0
        )
        p2p_earthquake_service = P2PEarthquakeService(p2p_config)
        await p2p_earthquake_service.initialize()
        
        # Register callbacks for real-time data processing
        def on_earthquake_callback(data: JMAQuake):
            logger.info(f"P2P地震情報受信: {data.earthquake.hypocenter.name if data.earthquake.hypocenter else '不明'} M{data.earthquake.hypocenter.magnitude if data.earthquake.hypocenter else '不明'}")
        
        def on_tsunami_callback(data: JMATsunami):
            logger.info(f"P2P津波予報受信: {'解除' if data.cancelled else '発表'}")
        
        async def on_eew_callback(data: EEW):
            if not data.cancelled and data.earthquake:
                logger.warning(f"緊急地震速報: {data.earthquake.hypocenter.name} M{data.earthquake.hypocenter.magnitude}")
                # Broadcast EEW to all WebSocket clients
                eew_data = {
                    "type": "emergency_earthquake_warning",
                    "data": {
                        "id": data.id,
                        "eventId": data.issue.eventId,
                        "serial": data.issue.serial,
                        "location": data.earthquake.hypocenter.name,
                        "magnitude": data.earthquake.hypocenter.magnitude,
                        "issued_at": data.issue.time,
                        "test": data.test or False
                    },
                    "timestamp": datetime.now().isoformat()
                }
                await broadcast_to_websockets(eew_data)
        
        p2p_earthquake_service.register_callback(InformationCode.JMA_QUAKE.value, on_earthquake_callback)
        p2p_earthquake_service.register_callback(InformationCode.JMA_TSUNAMI.value, on_tsunami_callback)
        p2p_earthquake_service.register_callback(InformationCode.EEW.value, on_eew_callback)
        
        # Start WebSocket monitoring in background (only if enabled)
        if p2p_config.enable_websocket:
            asyncio.create_task(p2p_earthquake_service.start_websocket_monitoring())
            logger.info("✓ P2P地震情報サービス初期化完了 (WebSocket監視開始)")
        else:
            logger.info("✓ P2P地震情報サービス初期化完了 (HTTP APIモード)")
    except Exception as e:
        logger.error(f"Failed to initialize P2P earthquake service: {e}")
        p2p_earthquake_service = None
    
    # Initialize YouTube chat analyzer
    try:
        # Get video ID from environment, use a default for development
        video_id = os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode')
        logger.info(f"Initializing chat analyzer with video_id: {video_id}")
        
        chat_analyzer = YouTubeChatAnalyzer(video_id)
        logger.info("YouTubeChatAnalyzer instance created successfully")
        
        # Only start monitoring if we have a real video ID
        if video_id != 'development_mode':
            # Start chat monitoring in background
            asyncio.create_task(monitor_chat())
            logger.info("YouTube chat analyzer initialized and monitoring started")
        else:
            logger.info("YouTube chat analyzer initialized in development mode (no real monitoring)")
            
        logger.info("✓ Chat analyzer initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize chat analyzer: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Don't fail completely - set chat_analyzer to None but continue
        chat_analyzer = None
    
    # Initialize social media automation service
    try:
        global social_media_automation
        social_media_automation = await init_social_media_automation()
        logger.info("✓ Social media automation service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize social media automation: {e}")
        social_media_automation = None
    
    # Initialize and start AMeDAS scheduler for hourly JSON export updates
    try:
        amedas_scheduler = get_scheduler(
            db_path="amedas_data.db", 
            update_interval=3600,
            export_json=False,  # JSON export handled by jma_amedas_scraper.py via cron
            json_path="amedas_data.json"
        )
        await amedas_scheduler.start()
        logger.info("✓ AMeDAS scheduler started - database tracking enabled (JSON created by cron job)")
    except Exception as e:
        logger.error(f"Failed to start AMeDAS scheduler: {e}")
        amedas_scheduler = None
    
    # Start global periodic updates task
    try:
        periodic_update_task = asyncio.create_task(global_periodic_updates())
        logger.info("✓ Global periodic updates task started")
    except Exception as e:
        logger.error(f"Failed to start periodic updates task: {e}")
        periodic_update_task = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down Disaster Information System backend...")
    
    # Stop AMeDAS scheduler
    if amedas_scheduler:
        try:
            await amedas_scheduler.stop()
            logger.info("✓ AMeDAS scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping AMeDAS scheduler: {e}")
    
    # Cancel periodic updates task
    if periodic_update_task and not periodic_update_task.done():
        periodic_update_task.cancel()
        try:
            await periodic_update_task
        except asyncio.CancelledError:
            logger.info("✓ Periodic updates task cancelled")
    
    # Cleanup P2P earthquake service
    if p2p_earthquake_service:
        p2p_earthquake_service.stop_websocket_monitoring()
        await p2p_earthquake_service.cleanup()
        logger.info("✓ P2P earthquake service cleaned up")
    
    if chat_analyzer:
        if hasattr(chat_analyzer, 'stop_monitoring'):
            chat_analyzer.stop_monitoring()
    
    if disaster_api_service and disaster_api_service.iij_websocket:
        await disaster_api_service.iij_websocket.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Disaster Information System API",
    description="Backend API for real-time disaster information, YouTube integration, and social media automation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",  # Next.js dev servers
        "http://49.212.176.130:3000",  # Remote server frontend
        "http://49.212.176.130:3001",  # Remote server frontend alternative port
        "http://49.212.176.130",  # Remote server root
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Provide a lightweight favicon handler to avoid 404/500 errors
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# Background task for monitoring chat
async def monitor_chat():
    """Background task to monitor YouTube live chat"""
    if not chat_analyzer:
        return
    
    try:
        await chat_analyzer.start_monitoring()
    except Exception as e:
        logger.error(f"Chat monitoring error: {e}")


def _generate_mock_earthquake_data():
    """Generate mock earthquake data for fallback purposes"""
    import random
    
    mock_earthquakes = []
    for i in range(random.randint(3, 8)):
        hours_ago = random.randint(1, 48)
        magnitude = round(random.uniform(3.0, 6.5), 1)
        depth = random.randint(10, 100)
        
        locations = [
            {"name": "東京湾", "lat": 35.6762, "lon": 139.6503},
            {"name": "千葉県東方沖", "lat": 35.7601, "lon": 140.4097},
            {"name": "静岡県伊豆地方", "lat": 34.9756, "lon": 138.9754},
            {"name": "福島県沖", "lat": 37.7503, "lon": 141.4676},
            {"name": "熊本県熊本地方", "lat": 32.7898, "lon": 130.7417},
            {"name": "宮城県沖", "lat": 38.2682, "lon": 140.8694},
            {"name": "神奈川県西部", "lat": 35.4033, "lon": 139.3428},
            {"name": "茨城県北部", "lat": 36.7073, "lon": 140.4467}
        ]
        
        location = random.choice(locations)
        
        # Determine intensity based on magnitude
        if magnitude >= 6.0:
            intensities = ["5+", "6-", "6+"]
        elif magnitude >= 5.0:
            intensities = ["4", "5-", "5+"]
        else:
            intensities = ["2", "3", "4"]
        
        intensity = random.choice(intensities)
        tsunami = magnitude >= 6.0 and random.random() < 0.3
        
        mock_earthquakes.append({
            "id": f"mock_eq_{i}_{int(datetime.now().timestamp())}",
            "time": (datetime.now() - timedelta(hours=hours_ago)).isoformat(),
            "location": location["name"],
            "magnitude": magnitude,
            "depth": depth,
            "latitude": location["lat"],
            "longitude": location["lon"],
            "intensity": intensity,
            "tsunami": tsunami
        })
    
    return mock_earthquakes


# Load station coordinates once at startup
_station_coordinates = None

def load_station_coordinates():
    """Load AMeDAS station coordinates from JSON file"""
    global _station_coordinates
    if _station_coordinates is None:
        try:
            coords_path = "amedas_station_coordinates.json"
            if os.path.exists(coords_path):
                with open(coords_path, 'r', encoding='utf-8') as f:
                    _station_coordinates = json.load(f)
                logger.info(f"Loaded coordinates for {len(_station_coordinates)} AMeDAS stations")
            else:
                logger.warning(f"Station coordinates file not found: {coords_path}")
                _station_coordinates = {}
        except Exception as e:
            logger.error(f"Error loading station coordinates: {e}")
            _station_coordinates = {}
    return _station_coordinates


# Helper function to get wind data from AMeDAS JSON export
async def get_wind_data_from_json():
    """Get wind data from AMeDAS JSON export file (scraped data updated hourly)"""
    try:
        import json
        import os
        
        json_path = "amedas_data.json"
        
        # Check if file exists
        if not os.path.exists(json_path):
            logger.warning(f"AMeDAS JSON file not found: {json_path}")
            return []
        
        # Read JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            logger.warning("No data found in AMeDAS JSON file")
            return []
        
        # Load station coordinates
        coordinates = load_station_coordinates()
        
        # Extract observations from all regions
        all_observations = []
        for region in data:
            for obs in region.get('observations', []):
                all_observations.append(obs)
        
        # Convert to wind data format
        wind_data = []
        for obs in all_observations:
            # Only include observations with wind data
            wind_speed_str = obs.get('wind_speed')
            if wind_speed_str and wind_speed_str != '---':
                try:
                    # Convert wind speed from m/s to km/h
                    wind_speed_ms = float(wind_speed_str)
                    wind_speed_kmh = wind_speed_ms * 3.6
                    
                    # Determine status based on wind speed (km/h)
                    # Thresholds: 0-25.2 km/h (0-7 m/s): calm/normal
                    #             25.2-36 km/h (7-10 m/s): moderate
                    #             36-54 km/h (10-15 m/s): warning
                    #             54+ km/h (15+ m/s): danger
                    if wind_speed_kmh >= 54:  # 15+ m/s
                        status = "danger"
                    elif wind_speed_kmh >= 36:  # 10-15 m/s
                        status = "warning"
                    elif wind_speed_kmh >= 25.2:  # 7-10 m/s
                        status = "moderate"
                    else:  # 0-7 m/s
                        status = "normal"
                    
                    # Calculate gusts (estimated as 1.5x average wind speed)
                    gusts_kmh = wind_speed_kmh * 1.5
                    
                    # Parse temperature
                    temp_str = obs.get('temperature', '---')
                    if temp_str and temp_str != '---':
                        temp_display = f"{float(temp_str):.1f}°C"
                    else:
                        temp_display = "--°C"
                    
                    # Parse humidity
                    humidity_str = obs.get('humidity', '---')
                    if humidity_str and humidity_str != '---':
                        humidity_display = f"{float(humidity_str):.0f}%"
                    else:
                        humidity_display = "--%"
                    
                    location_name = obs.get('location_name', 'Unknown')
                    
                    # Build wind data object
                    wind_point = {
                        "location": location_name,
                        "speed": f"{wind_speed_kmh:.1f} km/h",
                        "direction": obs.get('wind_direction', 'N/A'),
                        "gusts": f"{gusts_kmh:.1f} km/h",
                        "status": status,
                        "timestamp": obs.get('observation_time', ''),
                        "temperature": temp_display,
                        "humidity": humidity_display,
                        "source": "amedas_json_export"
                    }
                    
                    # Add coordinates if available
                    if location_name in coordinates:
                        wind_point["lat"] = coordinates[location_name]["lat"]
                        wind_point["lng"] = coordinates[location_name]["lng"]
                    
                    wind_data.append(wind_point)
                except (ValueError, TypeError) as e:
                    # Skip observations with invalid wind speed data
                    continue
        
        logger.info(f"Retrieved {len(wind_data)} wind observations from AMeDAS JSON file")
        return wind_data
        
    except Exception as e:
        logger.error(f"Error getting wind data from JSON: {e}")
        return []


# Helper function to get wind data (now uses JSON export)
async def get_current_wind_data_helper():
    """Get current wind data for WebSocket updates - reads from AMeDAS JSON export"""
    try:
        # Get wind data from the scraped AMeDAS JSON file
        wind_data = await get_wind_data_from_json()
        
        if wind_data:
            return wind_data
        
        # If no JSON data, log warning
        logger.warning("No wind data available from AMeDAS JSON export")
        return []
        
    except Exception as e:
        logger.error(f"Error getting wind data: {e}")
        return []


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat and disaster updates"""
    await websocket.accept()
    connected_websockets.append(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(connected_websockets)}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to disaster information system",
            "timestamp": datetime.now().isoformat()
        })
        
        # Send initial wind data
        try:
            initial_wind_data = await get_current_wind_data_helper()
            await websocket.send_json({
                "type": "wind_data_update",
                "wind_data": initial_wind_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending initial wind data: {e}")
        
        # Send initial news data
        try:
            initial_news_data = await fetch_real_time_news()
            await websocket.send_json({
                "type": "news_update",
                "news": [article.dict() for article in initial_news_data],
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending initial news data: {e}")
        
        # Send initial camera feeds data
        try:
            initial_camera_data = await fetch_real_time_camera_feeds()
            await websocket.send_json({
                "type": "camera_feeds_update",
                "camera_feeds": [feed.dict() for feed in initial_camera_data],
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending initial camera feeds data: {e}")
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.debug(f"Received WebSocket message: {message}")
                
                # Handle ping messages
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected (normal)")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from WebSocket: {e}")
                # Continue listening for more messages
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
        logger.info(f"WebSocket connection cleaned up. Remaining connections: {len(connected_websockets)}")


async def broadcast_to_websockets(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    if not connected_websockets:
        return
    
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(data)
        except Exception as e:
            logger.debug(f"Failed to send to WebSocket client: {e}")
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)
    
    if disconnected:
        logger.info(f"Removed {len(disconnected)} disconnected WebSocket clients. Active connections: {len(connected_websockets)}")


# API Routes

@app.get("/", response_model=dict)
async def root():
    """API information and available endpoints"""
    return {
        "message": "Disaster Information System API",
        "version": "1.0.0",
        "description": "Real-time disaster monitoring, YouTube integration, and social media automation",
        "docs": "/docs",
        "status": "running",
        "services": {
            "chat_analyzer": chat_analyzer is not None,
            "youtube_search": youtube_search_service is not None,
            "disaster_apis": disaster_api_service is not None,
            "p2p_earthquake": p2p_earthquake_service is not None
        },
        "endpoints": {
            "health": "/api/health",
            "disasters": "/api/disasters",
            "earthquakes": "/api/earthquakes",
            "earthquakes_comprehensive": "/api/disasters/earthquakes/comprehensive",
            "tsunami_alerts": "/api/disasters/tsunami",
            "recent_alerts": "/api/disasters/alerts/recent",
            "seismic_hazard": "/api/disasters/seismic-hazard",
            # P2P地震情報 API v2 endpoints
            "p2p_history": "/api/p2p/history",
            "p2p_jma_quakes": "/api/p2p/jma/quakes",
            "p2p_jma_quake": "/api/p2p/jma/quake/{id}",
            "p2p_jma_tsunamis": "/api/p2p/jma/tsunamis",
            "p2p_jma_tsunami": "/api/p2p/jma/tsunami/{id}",
            "p2p_latest_earthquakes": "/api/p2p/earthquakes/latest",
            "p2p_latest_tsunamis": "/api/p2p/tsunamis/latest",
            "p2p_latest_eew": "/api/p2p/eew/latest",
            "p2p_status": "/api/p2p/status",
            "news": "/api/news",
            "chat": "/api/chat",
            "analytics": "/api/analytics",
            "youtube_search": "/api/youtube/search",
            "youtube_video_details": "/api/youtube/video/{video_id}",
            "youtube_live_streams": "/api/youtube/live-streams",
            "youtube_channels": "/api/youtube/channels",
            "youtube_location_search": "/api/youtube/location/{location}",
            "youtube_trending": "/api/youtube/trending",
            "youtube_advanced_search": "/api/youtube/search/advanced",
            "websocket": "/ws"
        },
        "p2p_earthquake_features": {
            "realtime_websocket": {
                "description": "Real-time earthquake data via WebSocket",
                "information_codes": {
                    "551": "地震情報 (JMA Earthquake Information)",
                    "552": "津波予報 (JMA Tsunami Forecast)",
                    "554": "緊急地震速報発表検出 (EEW Detection)",
                    "555": "各地域ピア数 (Area Peer Count)",
                    "556": "緊急地震速報（警報） (Emergency Earthquake Warning)",
                    "561": "地震感知情報 (User Earthquake Detection)",
                    "9611": "地震感知情報解析結果 (User Earthquake Evaluation)"
                }
            },
            "historical_data": {
                "description": "Historical earthquake and tsunami data",
                "endpoints": ["/api/p2p/history", "/api/p2p/jma/quakes", "/api/p2p/jma/tsunamis"]
            },
            "filtering_options": {
                "magnitude_range": "Filter by minimum/maximum magnitude",
                "scale_intensity": "Filter by seismic intensity (震度)",
                "date_range": "Filter by date range (since_date/until_date)",
                "quake_type": "Filter by earthquake information type",
                "prefectures": "Filter by specific prefectures"
            },
            "rate_limits": {
                "history_api": "60 requests/minute per IP",
                "jma_api": "10 requests/minute per IP",
                "websocket": "Real-time with automatic reconnection"
            }
        },
        "youtube_search_features": {
            "basic_search": {
                "endpoint": "/api/youtube/search",
                "description": "Enhanced video search with filtering",
                "parameters": [
                    "query", "limit", "search_type", "time_filter", 
                    "quality_filter", "include_shorts"
                ],
                "search_types": ["general", "live", "recent", "channels"],
                "time_filters": ["today", "this_week", "this_month"],
                "quality_filters": ["hd", "4k"]
            },
            "video_details": {
                "endpoint": "/api/youtube/video/{video_id}",
                "description": "Get detailed information about specific videos",
                "features": ["metadata", "channel_info", "categories", "tags"]
            },
            "live_streams": {
                "endpoint": "/api/youtube/live-streams",
                "description": "Find live disaster broadcasts",
                "parameters": ["location"],
                "default_location": "Japan"
            },
            "channel_search": {
                "endpoint": "/api/youtube/channels",
                "description": "Find disaster information channels",
                "sorting": "by_subscriber_count",
                "verified_channels": "included"
            },
            "location_search": {
                "endpoint": "/api/youtube/location/{location}",
                "description": "Location-specific disaster content",
                "parameters": ["disaster_type", "limit"],
                "disaster_types": ["earthquake", "tsunami", "typhoon", "disaster_prep"]
            },
            "trending_topics": {
                "endpoint": "/api/youtube/trending",
                "description": "Trending disaster-related topics",
                "parameters": ["region"],
                "features": ["keyword_analysis", "related_searches"]
            },
            "advanced_search": {
                "endpoint": "/api/youtube/search/advanced",
                "description": "Comprehensive search with all features",
                "returns": ["videos", "channels", "live_streams", "trending_topics"],
                "features": ["multi_filter", "aggregated_results", "performance_metrics"]
            }
        },
        "api_sources": {
            "earthquake_data": ["P2P地震情報 API v2", "P2P地震情報", "USGS", "IIJ Engineering"],
            "tsunami_alerts": ["P2P地震情報 API v2", "P2P地震情報", "JMA"],
            "emergency_warnings": ["P2P地震情報 緊急地震速報"],
            "youtube_search": ["SerpApi - Enhanced YouTube Search API"],
            "youtube_video_details": ["SerpApi - YouTube Video API"],
            "seismic_hazard": ["J-SHIS"],
            "real_time_monitoring": ["P2P地震情報 WebSocket API", "IIJ WebSocket"]
        },
        "serpapi_features": {
            "search_engines": ["youtube", "youtube_video"],
            "filters_supported": [
                "time_based", "quality_based", "content_type", 
                "location_based", "channel_specific"
            ],
            "localization": {
                "countries": "configurable (default: jp)",
                "languages": "configurable (default: ja)"
            },
            "content_types": [
                "videos", "live_streams", "shorts", "channels", "playlists"
            ],
            "advanced_features": [
                "trending_analysis", "keyword_extraction", "duplicate_removal",
                "metadata_enrichment", "performance_monitoring"
            ]
        },
        "rate_limiting": {
            "youtube_search": "Built-in delays between requests",
            "p2p_earthquake": "Complies with P2P地震情報 rate limits",
            "concurrent_requests": "Managed automatically",
            "api_quota": "Monitored per SerpApi limits"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "chat_analyzer": chat_analyzer is not None,
            "youtube_search": youtube_search_service is not None,
            "disaster_apis": disaster_api_service is not None,
            "p2p_earthquake": p2p_earthquake_service is not None,
            "periodic_updates": periodic_update_task is not None and not periodic_update_task.done()
        },
        "p2p_earthquake_status": {
            "service_initialized": p2p_earthquake_service is not None,
            "websocket_monitoring": p2p_earthquake_service.is_monitoring if p2p_earthquake_service else False,
            "websocket_connected": p2p_earthquake_service.ws_connection is not None if p2p_earthquake_service else False,
            "environment": "sandbox" if p2p_earthquake_service and p2p_earthquake_service.config.use_sandbox else "production"
        } if p2p_earthquake_service else {"service_initialized": False},
        "websocket_connections": len(connected_websockets),
        "version": "1.0.0"
    }


@app.get("/api/websocket/status")
async def websocket_status():
    """WebSocket status endpoint"""
    return {
        "active_connections": len(connected_websockets),
        "periodic_updates_running": periodic_update_task is not None and not periodic_update_task.done(),
        "last_update": datetime.now().isoformat(),
        "connection_details": [
            {
                "client_state": ws.client_state.name if hasattr(ws, 'client_state') else "unknown",
                "application_state": ws.application_state.name if hasattr(ws, 'application_state') else "unknown"
            }
            for ws in connected_websockets
        ]
    }


@app.get("/api/disasters", response_model=List[DisasterAlert])
async def get_disaster_alerts():
    """Get current disaster alerts"""
    try:
        # This would integrate with actual disaster APIs
        # For now, return mock data
        alerts = [
            DisasterAlert(
                id="alert_001",
                type="earthquake",
                severity="moderate",
                location="Tokyo Metropolitan Area",
                message="Magnitude 5.2 earthquake detected. No tsunami warning issued.",
                timestamp=datetime.now(),
                coordinates={"lat": 35.6762, "lng": 139.6503}
            )
        ]
        return alerts
    except Exception as e:
        logger.error(f"Error fetching disaster alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch disaster alerts")


@app.get("/api/earthquakes", response_model=List[EarthquakeData])
async def get_earthquake_data():
    """Get recent earthquake data"""
    try:
        # This would integrate with USGS or JMA APIs
        earthquakes = [
            EarthquakeData(
                magnitude=5.2,
                location="35km E of Tokyo, Japan",
                depth=10.0,
                timestamp=datetime.now(),
                coordinates={"lat": 35.6762, "lng": 139.6503},
                intensity="Weak"
            )
        ]
        return earthquakes
    except Exception as e:
        logger.error(f"Error fetching earthquake data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch earthquake data")


async def fetch_real_time_news() -> List[NewsArticle]:
    """Fetch real-time news from multiple sources"""
    articles = []
    
    try:
        # Fetch from NHK News API
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(settings.nhk_news_api, timeout=10.0)
                if response.status_code == 200:
                    nhk_data = response.json()
                    # Parse NHK news format
                    if 'channel' in nhk_data and 'item' in nhk_data['channel']:
                        for item in nhk_data['channel']['item'][:5]:  # Limit to 5 items
                            articles.append(NewsArticle(
                                id=f"nhk_{item.get('guid', '')}",
                                title=item.get('title', ''),
                                summary=item.get('description', ''),
                                url=item.get('link', ''),
                                published_at=datetime.now() - timedelta(hours=random.randint(1, 6)),
                                category="official",
                                source="NHK",
                                time_ago=f"{random.randint(1, 6)}時間前"
                            ))
            except Exception as e:
                logger.warning(f"Failed to fetch NHK news: {e}")
        
        # Fetch from JMA (Japan Meteorological Agency) - Weather warnings
        try:
            async with httpx.AsyncClient() as client:
                # JMA weather warnings API
                jma_url = "https://www.jma.go.jp/bosai/warning/data/warning_info.json"
                response = await client.get(jma_url, timeout=10.0)
                if response.status_code == 200:
                    jma_data = response.json()
                    # Parse JMA warnings
                    if 'items' in jma_data:
                        for item in jma_data['items'][:3]:  # Limit to 3 items
                            articles.append(NewsArticle(
                                id=f"jma_{item.get('id', '')}",
                                title=f"気象警報: {item.get('name', '気象警報')}",
                                summary=item.get('description', '気象庁からの警報情報'),
                                url="https://www.jma.go.jp/bosai/warning/",
                                published_at=datetime.now() - timedelta(hours=random.randint(1, 4)),
                                category="weather",
                                source="気象庁",
                                time_ago=f"{random.randint(1, 4)}時間前"
                            ))
        except Exception as e:
            logger.warning(f"Failed to fetch JMA warnings: {e}")
        
        # Add government emergency guidelines (simulated real-time updates)
        articles.append(NewsArticle(
            id="gov_001",
            title="緊急時対応ガイドラインが更新されました",
            summary="防災管理庁から新しい緊急時対応ガイドラインが発表されました。",
            url="https://www.bousai.go.jp/",
            published_at=datetime.now() - timedelta(hours=2),
            category="official",
            source="防災管理庁",
            time_ago="2時間前"
        ))
        
        # Add training announcements
        articles.append(NewsArticle(
            id="local_001",
            title="地域緊急対応訓練のお知らせ",
            summary="地方自治体による緊急対応訓練が実施されます。",
            url="https://www.city.example.jp/",
            published_at=datetime.now() - timedelta(days=1),
            category="training",
            source="地方自治体",
            time_ago="1日前"
        ))
        
    except Exception as e:
        logger.error(f"Error in fetch_real_time_news: {e}")
    
    # Sort by published_at (most recent first)
    articles.sort(key=lambda x: x.published_at, reverse=True)
    return articles[:10]  # Return top 10 articles


@app.get("/api/news", response_model=List[NewsArticle])
async def get_news_articles():
    """Get recent disaster-related news articles from real-time sources"""
    try:
        articles = await fetch_real_time_news()
        return articles
    except Exception as e:
        logger.error(f"Error fetching news articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news articles")


async def fetch_real_time_camera_feeds() -> List[CameraFeed]:
    """Fetch real-time camera feed status and information"""
    feeds = []
    
    try:
        # Tokyo Bay Camera Feed
        feeds.append(CameraFeed(
            id="tokyo_bay_001",
            name="東京湾",
            status="online",
            location="東京都心部",
            stream_url="https://example.com/streams/tokyo_bay",
            thumbnail_url="https://example.com/thumbnails/tokyo_bay.jpg",
            last_updated=datetime.now(),
            coordinates={"lat": 35.6762, "lng": 139.6503}
        ))
        
        # Mount Fuji Camera Feed
        feeds.append(CameraFeed(
            id="fuji_001",
            name="富士山",
            status="online",
            location="静岡県",
            stream_url="https://example.com/streams/fuji",
            thumbnail_url="https://example.com/thumbnails/fuji.jpg",
            last_updated=datetime.now(),
            coordinates={"lat": 35.3606, "lng": 138.7274}
        ))
        
        # Osaka Port Camera Feed (simulate maintenance)
        feeds.append(CameraFeed(
            id="osaka_port_001",
            name="大阪港",
            status="maintenance",
            location="大阪府",
            stream_url=None,
            thumbnail_url="https://example.com/thumbnails/maintenance.jpg",
            last_updated=datetime.now() - timedelta(hours=2),
            coordinates={"lat": 34.6937, "lng": 135.5023}
        ))
        
        # Additional camera feeds for better coverage
        feeds.append(CameraFeed(
            id="yokohama_001",
            name="横浜港",
            status="online",
            location="神奈川県",
            stream_url="https://example.com/streams/yokohama",
            thumbnail_url="https://example.com/thumbnails/yokohama.jpg",
            last_updated=datetime.now(),
            coordinates={"lat": 35.4437, "lng": 139.6380}
        ))
        
        feeds.append(CameraFeed(
            id="nagoya_001",
            name="名古屋港",
            status="online",
            location="愛知県",
            stream_url="https://example.com/streams/nagoya",
            thumbnail_url="https://example.com/thumbnails/nagoya.jpg",
            last_updated=datetime.now(),
            coordinates={"lat": 35.0956, "lng": 136.8844}
        ))
        
        # Simulate some feeds being offline
        feeds.append(CameraFeed(
            id="kobe_001",
            name="神戸港",
            status="offline",
            location="兵庫県",
            stream_url=None,
            thumbnail_url="https://example.com/thumbnails/offline.jpg",
            last_updated=datetime.now() - timedelta(hours=1),
            coordinates={"lat": 34.6901, "lng": 135.1956}
        ))
        
    except Exception as e:
        logger.error(f"Error in fetch_real_time_camera_feeds: {e}")
    
    return feeds


@app.get("/api/camera-feeds", response_model=List[CameraFeed])
async def get_camera_feeds():
    """Get real-time camera feed status and information"""
    try:
        feeds = await fetch_real_time_camera_feeds()
        return feeds
    except Exception as e:
        logger.error(f"Error fetching camera feeds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch camera feeds")


@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Test successful", "timestamp": datetime.now().isoformat()}

@app.get("/api/chat/test")
async def test_chat_endpoint():
    """Test chat endpoint with minimal logic"""
    try:
        mock_message = {
            "id": "test_001",
            "message_id": "test_001",
            "author": "TestUser",
            "message": "Test message",
            "timestamp": datetime.now().isoformat(),
            "sentiment_score": 0.5,
            "category": "test",
            "platform": "youtube"
        }
        return [mock_message]
    except Exception as e:
        logger.error(f"Error in test chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@app.get("/api/chat/messages")
async def get_chat_messages(limit: int = 50):
    """Get recent YouTube chat messages with enhanced data"""
    try:
        # For development mode, return mock data FIRST
        if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
            mock_messages = [
                {
                    "id": "msg_001",
                    "message_id": "msg_001",
                    "author": "TestUser1",
                    "message": "Hello! Thank you for the disaster information",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.8,
                    "category": "general",
                    "platform": "youtube",
                    "message_type": "text"
                },
                {
                    "id": "msg_002", 
                    "message_id": "msg_002",
                    "author": "DisasterWatcher",
                    "message": "Please tell me about earthquake preparedness",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.1,
                    "category": "disaster",
                    "platform": "youtube",
                    "message_type": "text"
                },
                {
                    "id": "msg_003",
                    "message_id": "msg_003", 
                    "author": "PreparedCitizen",
                    "message": "Where can I buy disaster supplies?",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.5,
                    "category": "product",
                    "platform": "youtube",
                    "message_type": "text"
                },
                {
                    "id": "msg_004",
                    "message_id": "msg_004",
                    "author": "GenerousViewer", 
                    "message": "Thank you for the great information! Keep up the good work!",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.9,
                    "category": "general",
                    "platform": "youtube",
                    "message_type": "super_chat",
                    "amount_value": 500.0,
                    "currency": "JPY"
                }
            ]
            return mock_messages[:limit]
        
        # Check for chat analyzer only after development mode check
        if not chat_analyzer:
            raise HTTPException(status_code=503, detail="Chat analyzer not available")
        
        # Get real messages from the chat analyzer database
        try:
            messages = chat_analyzer.get_recent_messages(limit)
            logger.info(f"Retrieved {len(messages)} real chat messages from database")
            return messages
        except Exception as e:
            logger.error(f"Error getting messages from chat analyzer: {e}")
            # Fallback to empty list
            return []
            
    except Exception as e:
        logger.error(f"Error fetching chat messages: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat messages: {str(e)}")


@app.get("/api/chat/analytics", response_model=ChatAnalytics)
async def get_chat_analytics():
    """Get YouTube chat analytics with enhanced statistics"""
    # For development mode, return mock data FIRST
    if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
        return ChatAnalytics(
            total_messages=142,
            disaster_mentions=23,
            product_mentions=18,
            sentiment_score=0.6,
            top_keywords=["地震", "防災", "津波", "備え", "安全"],
            active_users=47
        )
    
    # Check for chat analyzer only after development mode check
    if not chat_analyzer:
        raise HTTPException(status_code=503, detail="Chat analyzer not available")
    
    try:
        # Get real analytics from the chat analyzer
        stats = chat_analyzer.get_chat_statistics(24)  # Last 24 hours
        
        # Convert to ChatAnalytics format
        return ChatAnalytics(
            total_messages=stats.get('total_messages', 0),
            disaster_mentions=stats.get('categories', {}).get('disaster', 0),
            product_mentions=stats.get('categories', {}).get('product', 0),
            sentiment_score=stats.get('average_sentiment', 0.0),
            top_keywords=[kw[0] for kw in stats.get('top_keywords', [])[:10]],  # Top 10 keywords
            active_users=stats.get('unique_users', 0)
        )
        
    except Exception as e:
        logger.error(f"Error fetching chat analytics: {e}")
        # Return fallback analytics
        return ChatAnalytics(
            total_messages=0,
            disaster_mentions=0,
            product_mentions=0,
            sentiment_score=0.0,
            top_keywords=[],
            active_users=0
        )


@app.post("/api/chat/response")
async def send_chat_response(request: dict):
    """Send a response to YouTube chat"""
    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # For development mode, return success FIRST
    if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
        return {"status": "success", "message": "Response sent (development mode)"}
    
    # Check for chat analyzer only after development mode check
    if not chat_analyzer:
        raise HTTPException(status_code=503, detail="Chat analyzer not available")
    
    try:
        # Real implementation would go here
        return {"status": "success", "message": "Response sent"}
    except Exception as e:
        logger.error(f"Error sending chat response: {e}")
        raise HTTPException(status_code=500, detail="Failed to send response")


@app.get("/api/chat/responses", response_model=List[AutoResponse])
async def get_auto_responses():
    """Get configured auto-responses from the enhanced system"""
    if not chat_analyzer:
        raise HTTPException(status_code=503, detail="Chat analyzer not available")
    
    # For development mode, return mock data
    if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
        mock_responses = [
            AutoResponse(
                id=1,
                trigger_keywords="こんにちは,hello,hi", 
                response_text="こんにちは！災害情報配信をご視聴いただき、ありがとうございます！🙋‍♀️",
                response_type="greeting",
                used_count=15,
                last_used_at=datetime.now().isoformat()
            ),
            AutoResponse(
                id=2,
                trigger_keywords="地震,earthquake",
                response_text="🚨 地震情報を確認中です。最新情報は画面の地震データをご確認ください。公式発表をお待ちください。",
                response_type="disaster",
                used_count=8,
                last_used_at=datetime.now().isoformat()
            ),
            AutoResponse(
                id=3,
                trigger_keywords="津波,tsunami",
                response_text="🌊 津波に関する情報は気象庁の公式発表をご確認ください。海岸近くの方は直ちに高台へ避難してください。",
                response_type="disaster",
                used_count=5,
                last_used_at=datetime.now().isoformat()
            ),
            AutoResponse(
                id=4,
                trigger_keywords="防災グッズ,disaster kit,emergency supplies",
                response_text="🎒 防災グッズの情報はこちらをご参考ください。非常食、懐中電灯、ラジオ、応急手当用品をご準備ください。",
                response_type="product",
                used_count=12,
                last_used_at=datetime.now().isoformat()
            )
        ]
        return mock_responses
    
    try:
        # Get real auto response rules from database
        import sqlite3
        conn = sqlite3.connect(chat_analyzer.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, keywords, response, response_type, used_count, last_used_at
            FROM response_rules 
            WHERE enabled = TRUE 
            ORDER BY priority
        ''')
        
        responses = []
        for row in cursor.fetchall():
            responses.append(AutoResponse(
                id=row[0],
                trigger_keywords=row[1],  # Keywords are stored as comma-separated string
                response_text=row[2],
                response_type=row[3],
                used_count=row[4] or 0,
                last_used_at=row[5] or datetime.now().isoformat()
            ))
        
        conn.close()
        logger.info(f"Retrieved {len(responses)} auto response rules from database")
        return responses
        
    except Exception as e:
        logger.error(f"Error fetching auto-responses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auto-responses")


# New Enhanced YouTube Search API Endpoints
@app.get("/api/youtube/search")
async def search_youtube_videos(
    query: str = None, 
    limit: int = 10,
    search_type: str = "general",
    time_filter: str = None,
    quality_filter: str = None,
    include_shorts: bool = True
):
    """Enhanced search for disaster-related YouTube videos with advanced filtering"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_disaster_videos(
            query=query,
            limit=limit,
            search_type=search_type,
            time_filter=time_filter,
            quality_filter=quality_filter,
            include_shorts=include_shorts
        )
        
        return {
            "videos": [
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel,
                    "description": video.description,
                    "thumbnail": video.thumbnail,
                    "duration": video.duration,
                    "views": video.views,
                    "published_time": video.published_time,
                    "link": video.link,
                    "channel_id": video.channel_id,
                    "channel_url": video.channel_url,
                    "subscriber_count": video.subscriber_count,
                    "video_type": video.video_type,
                    "verified_channel": video.verified_channel,
                    "category": video.category,
                    "tags": video.tags
                }
                for video in result.videos
            ],
            "channels": [
                {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "url": channel.url,
                    "thumbnail": channel.thumbnail,
                    "subscriber_count": channel.subscriber_count,
                    "verified": channel.verified,
                    "description": channel.description
                }
                for channel in result.channels
            ],
            "total_results": result.total_results,
            "search_query": result.search_query,
            "next_page_token": result.next_page_token,
            "related_searches": result.related_searches,
            "response_time": result.response_time,
            "search_parameters": {
                "search_type": search_type,
                "time_filter": time_filter,
                "quality_filter": quality_filter,
                "include_shorts": include_shorts
            }
        }
    except Exception as e:
        logger.error(f"Error searching YouTube videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to search YouTube videos")


@app.get("/api/youtube/video/{video_id}")
async def get_youtube_video_details(video_id: str):
    """Get detailed information about a specific YouTube video"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        video = await youtube_search_service.get_video_details(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return {
            "video_id": video.video_id,
            "title": video.title,
            "channel": video.channel,
            "description": video.description,
            "thumbnail": video.thumbnail,
            "duration": video.duration,
            "views": video.views,
            "published_time": video.published_time,
            "link": video.link,
            "channel_id": video.channel_id,
            "channel_url": video.channel_url,
            "subscriber_count": video.subscriber_count,
            "video_type": video.video_type,
            "verified_channel": video.verified_channel,
            "category": video.category,
            "tags": video.tags
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video details")


@app.get("/api/youtube/live-streams")
async def get_live_disaster_streams(location: str = "Japan"):
    """Get live disaster-related YouTube streams for a specific location"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_live_disaster_streams(location)
        return {
            "streams": [
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel,
                    "thumbnail": video.thumbnail,
                    "link": video.link,
                    "duration": video.duration,
                    "views": video.views,
                    "channel_id": video.channel_id,
                    "verified_channel": video.verified_channel,
                    "video_type": video.video_type
                }
                for video in result.videos
            ],
            "channels": [
                {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "url": channel.url,
                    "thumbnail": channel.thumbnail,
                    "subscriber_count": channel.subscriber_count,
                    "verified": channel.verified
                }
                for channel in result.channels
            ],
            "total_results": result.total_results,
            "location": location,
            "search_query": result.search_query
        }
    except Exception as e:
        logger.error(f"Error fetching live streams: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch live streams")


@app.get("/api/youtube/channels")
async def get_disaster_channels(limit: int = 10):
    """Get disaster information and news channels"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_disaster_channels(limit)
        return {
            "channels": [
                {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "url": channel.url,
                    "thumbnail": channel.thumbnail,
                    "subscriber_count": channel.subscriber_count,
                    "verified": channel.verified,
                    "description": channel.description
                }
                for channel in result.channels
            ],
            "total_results": result.total_results,
            "search_query": result.search_query
        }
    except Exception as e:
        logger.error(f"Error fetching disaster channels: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch disaster channels")


@app.get("/api/youtube/location/{location}")
async def search_by_location(
    location: str, 
    disaster_type: str = None, 
    limit: int = 20
):
    """Search for disaster content specific to a location"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_by_location(location, disaster_type, limit)
        return {
            "videos": [
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel,
                    "description": video.description,
                    "thumbnail": video.thumbnail,
                    "duration": video.duration,
                    "views": video.views,
                    "published_time": video.published_time,
                    "link": video.link,
                    "video_type": video.video_type,
                    "verified_channel": video.verified_channel
                }
                for video in result.videos
            ],
            "total_results": result.total_results,
            "location": location,
            "disaster_type": disaster_type,
            "search_query": result.search_query
        }
    except Exception as e:
        logger.error(f"Error searching by location: {e}")
        raise HTTPException(status_code=500, detail="Failed to search by location")


@app.get("/api/youtube/trending")
async def get_trending_disaster_topics(region: str = "JP"):
    """Get trending disaster-related topics on YouTube for a specific region"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        topics = await youtube_search_service.get_trending_disaster_topics(region)
        return {
            "trending_topics": topics,
            "region": region,
            "total_topics": len(topics)
        }
    except Exception as e:
        logger.error(f"Error fetching trending topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending topics")


@app.get("/api/youtube/search/advanced")
async def advanced_youtube_search(
    query: str = None,
    search_type: str = "general",
    time_filter: str = None,
    quality_filter: str = None,
    location: str = None,
    disaster_type: str = None,
    include_shorts: bool = True,
    include_channels: bool = True,
    limit: int = 20
):
    """Advanced YouTube search with multiple filter options and comprehensive results"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        results = {
            "videos": [],
            "channels": [],
            "live_streams": [],
            "trending_topics": [],
            "search_metadata": {
                "query": query,
                "search_type": search_type,
                "time_filter": time_filter,
                "quality_filter": quality_filter,
                "location": location,
                "disaster_type": disaster_type,
                "include_shorts": include_shorts,
                "include_channels": include_channels,
                "limit": limit
            }
        }
        
        # Primary video search
        video_result = await youtube_search_service.search_disaster_videos(
            query=query,
            limit=limit,
            search_type=search_type,
            time_filter=time_filter,
            quality_filter=quality_filter,
            include_shorts=include_shorts
        )
        
        results["videos"] = [
            {
                "video_id": video.video_id,
                "title": video.title,
                "channel": video.channel,
                "description": video.description,
                "thumbnail": video.thumbnail,
                "duration": video.duration,
                "views": video.views,
                "published_time": video.published_time,
                "link": video.link,
                "video_type": video.video_type,
                "verified_channel": video.verified_channel
            }
            for video in video_result.videos
        ]
        
        # Channel search if requested
        if include_channels:
            channel_result = await youtube_search_service.search_disaster_channels(limit // 2)
            results["channels"] = [
                {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "url": channel.url,
                    "thumbnail": channel.thumbnail,
                    "subscriber_count": channel.subscriber_count,
                    "verified": channel.verified,
                    "description": channel.description
                }
                for channel in channel_result.channels
            ]
        
        # Live streams
        if search_type in ['live', 'general']:
            live_result = await youtube_search_service.search_live_disaster_streams(location or "Japan")
            results["live_streams"] = [
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel,
                    "thumbnail": video.thumbnail,
                    "link": video.link,
                    "duration": video.duration,
                    "verified_channel": video.verified_channel
                }
                for video in live_result.videos[:5]  # Limit live streams
            ]
        
        # Trending topics
        trending = await youtube_search_service.get_trending_disaster_topics()
        results["trending_topics"] = trending[:10]  # Top 10 trending topics
        
        # Add summary statistics
        results["summary"] = {
            "total_videos": len(results["videos"]),
            "total_channels": len(results["channels"]),
            "total_live_streams": len(results["live_streams"]),
            "total_trending_topics": len(results["trending_topics"]),
            "response_time": video_result.response_time
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error in advanced YouTube search: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform advanced search")


# Enhanced Disaster API Endpoints
@app.get("/api/disasters/earthquakes/comprehensive")
async def get_comprehensive_earthquake_data():
    """Get comprehensive earthquake data from multiple sources"""
    if not disaster_api_service:
        raise HTTPException(status_code=503, detail="Disaster API service not available")
    
    try:
        earthquakes = await disaster_api_service.get_comprehensive_earthquake_data()
        return {
            "earthquakes": [
                {
                    "id": eq.id,
                    "magnitude": eq.magnitude,
                    "depth": eq.depth,
                    "latitude": eq.latitude,
                    "longitude": eq.longitude,
                    "location": eq.location,
                    "timestamp": eq.timestamp.isoformat(),
                    "intensity": eq.intensity,
                    "tsunami_warning": eq.tsunami_warning,
                    "source": eq.source
                }
                for eq in earthquakes
            ],
            "count": len(earthquakes),
            "sources": list(set(eq.source for eq in earthquakes))
        }
    except Exception as e:
        logger.error(f"Error fetching comprehensive earthquake data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch earthquake data")


@app.get("/api/disasters/tsunami")
async def get_tsunami_alerts():
    """Get current tsunami alerts"""
    if not disaster_api_service:
        raise HTTPException(status_code=503, detail="Disaster API service not available")
    
    try:
        tsunami_alerts = await disaster_api_service.get_tsunami_alerts()
        return {
            "tsunami_alerts": [
                {
                    "id": alert.id,
                    "area": alert.area,
                    "height_prediction": alert.height_prediction,
                    "arrival_time": alert.arrival_time.isoformat() if alert.arrival_time else None,
                    "alert_level": alert.alert_level.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "source": alert.source
                }
                for alert in tsunami_alerts
            ],
            "count": len(tsunami_alerts)
        }
    except Exception as e:
        logger.error(f"Error fetching tsunami alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tsunami alerts")


@app.get("/api/disasters/alerts/recent")
async def get_recent_disaster_alerts(hours: int = 24):
    """Get recent disaster alerts from all sources"""
    if not disaster_api_service:
        raise HTTPException(status_code=503, detail="Disaster API service not available")
    
    try:
        alerts = await disaster_api_service.get_recent_alerts(hours)
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "disaster_type": alert.disaster_type.value,
                    "title": alert.title,
                    "description": alert.description,
                    "location": alert.location,
                    "coordinates": alert.coordinates,
                    "alert_level": alert.alert_level.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "expiry_time": alert.expiry_time.isoformat() if alert.expiry_time else None,
                    "source": alert.source,
                    "additional_info": alert.additional_info
                }
                for alert in alerts
            ],
            "count": len(alerts),
            "time_range_hours": hours
        }
    except Exception as e:
        logger.error(f"Error fetching recent disaster alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent alerts")


@app.get("/api/disasters/seismic-hazard")
async def get_seismic_hazard_info(latitude: float, longitude: float):
    """Get seismic hazard information for specific coordinates"""
    if not disaster_api_service:
        raise HTTPException(status_code=503, detail="Disaster API service not available")
    
    try:
        hazard_info = await disaster_api_service.jshis_api.get_seismic_hazard_info(latitude, longitude)
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "hazard_info": hazard_info
        }
    except Exception as e:
        logger.error(f"Error fetching seismic hazard info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch seismic hazard information")


@app.get("/api/earthquake/recent")
async def get_recent_earthquake_data():
    """Get recent earthquake data for map display"""
    try:
        # Use real disaster API service if available
        if disaster_api_service:
            earthquakes = await disaster_api_service.get_comprehensive_earthquake_data()
            
            if earthquakes:
                # Convert to format expected by the map component
                formatted_earthquakes = [
                    {
                        "id": eq.id,
                        "time": eq.timestamp.isoformat(),
                        "location": eq.location,
                        "magnitude": eq.magnitude,
                        "depth": eq.depth,
                        "latitude": eq.latitude,
                        "longitude": eq.longitude,
                        "intensity": eq.intensity,
                        "tsunami": eq.tsunami_warning
                    }
                    for eq in earthquakes
                ]
                logger.info(f"Returning {len(formatted_earthquakes)} real earthquake records from {set(eq.source for eq in earthquakes)}")
                return formatted_earthquakes
        
        # Fallback to mock data if no real data available
        logger.info("Using mock earthquake data - no real API data available")
        import random
        mock_earthquakes = [
            {
                "id": "mock_eq_1",
                "time": (datetime.now() - timedelta(hours=2)).isoformat(),
                "location": "東京湾",
                "magnitude": 4.5,
                "depth": 80,
                "latitude": 35.6762,
                "longitude": 139.6503,
                "intensity": "4",
                "tsunami": False
            },
            {
                "id": "mock_eq_2", 
                "time": (datetime.now() - timedelta(hours=6)).isoformat(),
                "location": "千葉県東方沖",
                "magnitude": 5.2,
                "depth": 50,
                "latitude": 35.7601,
                "longitude": 140.4097,
                "intensity": "5-",
                "tsunami": False
            },
            {
                "id": "mock_eq_3",
                "time": (datetime.now() - timedelta(hours=12)).isoformat(),
                "location": "静岡県伊豆地方",
                "magnitude": 3.8,
                "depth": 10,
                "latitude": 34.9756,
                "longitude": 138.9754,
                "intensity": "3",
                "tsunami": False
            },
            {
                "id": "mock_eq_4",
                "time": (datetime.now() - timedelta(hours=18)).isoformat(),
                "location": "福島県沖",
                "magnitude": 4.1,
                "depth": 45,
                "latitude": 37.7503,
                "longitude": 141.4676,
                "intensity": "3",
                "tsunami": False
            },
            {
                "id": "mock_eq_5",
                "time": (datetime.now() - timedelta(hours=24)).isoformat(),
                "location": "熊本県熊本地方",
                "magnitude": 3.9,
                "depth": 15,
                "latitude": 32.7898,
                "longitude": 130.7417,
                "intensity": "3",
                "tsunami": False
            }
        ]
        return mock_earthquakes
        
    except Exception as e:
        logger.error(f"Error fetching earthquake data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch earthquake data")

@app.get("/api/tsunami/alerts")
async def get_tsunami_alert_data():
    """Get tsunami alerts for map display"""
    try:
        # Use real disaster API service if available
        if disaster_api_service:
            tsunami_alerts = await disaster_api_service.get_tsunami_alerts()
            
            if tsunami_alerts:
                # Convert to format expected by the map component
                formatted_alerts = [
                    {
                        "id": alert.id,
                        "location": alert.area,
                        "level": alert.alert_level.value,
                        "time": alert.timestamp.isoformat(),
                        "latitude": 35.6762,  # Default coordinates - would need geocoding for real locations
                        "longitude": 139.6503
                    }
                    for alert in tsunami_alerts
                ]
                logger.info(f"Returning {len(formatted_alerts)} real tsunami alerts")
                return formatted_alerts
        
        # Fallback to mock data if no real data available
        logger.info("Using mock tsunami data - no real API data available")
        import random
        mock_tsunamis = [
            {
                "id": "mock_tsunami_1",
                "location": "宮城県沿岸",
                "level": "warning",
                "time": (datetime.now() - timedelta(hours=1)).isoformat(),
                "latitude": 38.2682,
                "longitude": 140.8694
            },
            {
                "id": "mock_tsunami_2",
                "location": "静岡県沿岸",
                "level": "advisory",
                "time": (datetime.now() - timedelta(hours=3)).isoformat(),
                "latitude": 34.9756,
                "longitude": 138.3828
            }
        ]
        return mock_tsunamis
        
    except Exception as e:
        logger.error(f"Error fetching tsunami alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tsunami alerts")


@app.get("/api/weather/amedas/station-coordinates")
async def get_station_coordinates():
    """Get AMeDAS station coordinates for all stations"""
    try:
        import json
        import os
        
        coords_file = "amedas_station_coordinates.json"
        
        # Check if file exists
        if not os.path.exists(coords_file):
            logger.warning(f"Station coordinates file not found: {coords_file}")
            return JSONResponse(content={}, media_type="application/json; charset=utf-8")
        
        # Read coordinates file
        with open(coords_file, 'r', encoding='utf-8') as f:
            coordinates = json.load(f)
        
        logger.info(f"Returning coordinates for {len(coordinates)} stations")
        
        return JSONResponse(
            content=coordinates,
            media_type="application/json; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error fetching station coordinates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch station coordinates")


@app.get("/api/weather/wind")
async def get_wind_data():
    """Get wind data from AMeDAS JSON export (scraped data, updated hourly)"""
    try:
        # Use JSON helper to get scraped AMeDAS data
        wind_data = await get_wind_data_from_json()
        
        logger.info(f"Returning wind data for {len(wind_data)} stations from AMeDAS JSON export")
        
        # Return JSON response with explicit UTF-8 encoding
        return JSONResponse(
            content=wind_data,
            media_type="application/json; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error fetching wind data from JSON export: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind data from JSON export")


@app.get("/api/weather/wind/jma")
async def get_jma_wind_data():
    """Get comprehensive wind data from JMA AMeDAS stations"""
    try:
        wind_service = get_wind_service()
        wind_data = await wind_service.get_current_wind_data()
        
        # Convert to dict format
        result = [w.to_dict() for w in wind_data]
        
        logger.info(f"Returning JMA wind data for {len(result)} stations")
        
        return JSONResponse(
            content=result,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error fetching JMA wind data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch JMA wind data")


@app.get("/api/weather/wind/summary")
async def get_wind_summary():
    """Get summary of current wind conditions across Japan"""
    try:
        wind_service = get_wind_service()
        summary = await wind_service.get_wind_summary()
        
        return JSONResponse(
            content=summary,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error fetching wind summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind summary")


@app.get("/api/weather/wind/map")
async def get_wind_map_data():
    """Get wind data formatted for map display (GeoJSON)"""
    try:
        wind_service = get_wind_service()
        map_data = await wind_service.get_wind_map_data()
        
        return JSONResponse(
            content=map_data,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error fetching wind map data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind map data")


@app.get("/api/weather/amedas")
async def get_amedas_data(limit: int = Query(20, ge=1, le=100, description="Number of stations to return")):
    """Get real-time weather data from AMEDAS JSON file
    
    Returns temperature, wind speed, wind direction, and humidity data from the latest observations.
    """
    try:
        # Load data from JSON file
        json_path = "amedas_data.json"
        if not os.path.exists(json_path):
            logger.warning(f"AMEDAS data file not found: {json_path}")
            return []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            logger.warning("No AMEDAS data available in JSON file")
            return []
        
        # Collect all observations from all regions
        all_observations = []
        for region in data:
            for obs in region.get('observations', []):
                all_observations.append(obs)
        
        if not all_observations:
            logger.warning("No observations found in AMEDAS data")
            return []
        
        # Format data for frontend (matching WindData interface)
        formatted_data = []
        for obs in all_observations[:limit]:
            # Parse wind speed
            wind_speed_str = obs.get('wind_speed', '0')
            try:
                wind_speed_ms = float(wind_speed_str) if wind_speed_str and wind_speed_str != '---' else 0
            except (ValueError, TypeError):
                wind_speed_ms = 0
            
            # Convert wind speed from m/s to km/h for display
            wind_speed_kmh = wind_speed_ms * 3.6
            
            # Determine status based on wind speed (km/h)
            if wind_speed_kmh > 60:
                status = 'error'
            elif wind_speed_kmh > 30:
                status = 'moderate'
            elif wind_speed_kmh < 10:
                status = 'calm'
            else:
                status = 'normal'
            
            # Calculate gusts (estimated as 1.5x average wind speed)
            gusts_kmh = wind_speed_kmh * 1.5
            
            # Parse temperature
            temp_str = obs.get('temperature', '0')
            try:
                temp = float(temp_str) if temp_str and temp_str != '---' else None
            except (ValueError, TypeError):
                temp = None
            
            # Parse humidity
            humidity_str = obs.get('humidity', '0')
            try:
                humidity = float(humidity_str) if humidity_str and humidity_str != '---' else None
            except (ValueError, TypeError):
                humidity = None
            
            formatted_data.append({
                'location': obs.get('location_name', 'Unknown'),
                'speed': f"{wind_speed_kmh:.1f} km/h",
                'direction': obs.get('wind_direction', 'N/A'),
                'gusts': f"{gusts_kmh:.1f} km/h",
                'status': status,
                'timestamp': obs.get('observation_time', ''),
                'temperature': f"{temp:.1f}°C" if temp is not None else 'N/A',
                'humidity': f"{humidity:.0f}%" if humidity is not None else 'N/A'
            })
        
        logger.info(f"Returning AMEDAS data for {len(formatted_data)} stations")
        
        return JSONResponse(
            content=formatted_data,
            media_type="application/json; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error fetching AMEDAS data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch AMEDAS data: {str(e)}")


@app.post("/api/streaming/start")
async def start_youtube_streaming(stream_key: str = Query(..., description="YouTube Live stream key")):
    """Start streaming the dashboard to YouTube Live"""
    try:
        streamer = get_streamer(stream_key)
        
        if streamer.is_streaming:
            return {
                "status": "already_streaming",
                "message": "Streaming is already active"
            }
        
        success = streamer.start_streaming_with_browser()
        
        if success:
            return {
                "status": "started",
                "message": "YouTube Live streaming started successfully",
                "stream_info": streamer.get_status()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start streaming")
    
    except Exception as e:
        logger.error(f"Error starting YouTube streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/streaming/stop")
async def stop_youtube_streaming():
    """Stop YouTube Live streaming"""
    try:
        streamer = get_streamer("")
        
        if not streamer.is_streaming:
            return {
                "status": "not_streaming",
                "message": "No active stream to stop"
            }
        
        success = streamer.stop_streaming()
        
        if success:
            return {
                "status": "stopped",
                "message": "YouTube Live streaming stopped successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop streaming")
    
    except Exception as e:
        logger.error(f"Error stopping YouTube streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/streaming/status")
async def get_streaming_status():
    """Get current YouTube Live streaming status"""
    try:
        streamer = get_streamer("")
        status = streamer.get_status()
        
        return JSONResponse(
            content=status,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/streaming/obs-config")
async def get_obs_config(stream_key: str = Query(..., description="YouTube Live stream key")):
    """Generate OBS Studio configuration for streaming"""
    try:
        config = OBSStreamingConfig.generate_obs_config(stream_key)
        
        return JSONResponse(
            content=config,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error generating OBS config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commentary/current")
async def get_current_commentary():
    """Generate AI commentary for current disaster events"""
    try:
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if not openai_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        commentary_service = get_commentary_service(openai_key)
        commentaries = await commentary_service.generate_commentary_for_current_events()
        
        result = [c.to_dict() for c in commentaries]
        
        return JSONResponse(
            content=result,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error generating commentary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commentary/history")
async def get_commentary_history(limit: int = Query(10, description="Number of recent commentaries to return")):
    """Get recent commentary history"""
    try:
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if not openai_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        commentary_service = get_commentary_service(openai_key)
        history = commentary_service.commentary_history[-limit:]
        
        result = [c.to_dict() for c in history]
        
        return JSONResponse(
            content=result,
            media_type="application/json; charset=utf-8"
        )
    
    except Exception as e:
        logger.error(f"Error fetching commentary history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/messages")
async def debug_get_messages():
    """Debug endpoint to get all messages"""
    return {"messages": chat_messages, "count": len(chat_messages)}


# Include the API router (for future organization)
# Note: Current routes are already on app directly, but this sets up future organization
# app.include_router(api_router)

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": f"The requested endpoint was not found"}
    )


@app.websocket("/ws/test")
async def test_websocket_endpoint(websocket: WebSocket):
    """Simple test WebSocket endpoint for debugging connections"""
    try:
        await websocket.accept()
        logger.info("Test WebSocket client connected")
        
        # Send initial test message
        await websocket.send_json({
            "type": "test_connection",
            "message": "Test WebSocket connection successful",
            "timestamp": datetime.now().isoformat()
        })
        
        # Simple echo server
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Echo back with timestamp
                await websocket.send_json({
                    "type": "echo",
                    "original": message,
                    "timestamp": datetime.now().isoformat()
                })
                
            except WebSocketDisconnect:
                logger.info("Test WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"Test WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"Test WebSocket connection error: {e}")


@app.get("/api/test/websocket")
async def test_websocket_info():
    """Information about test WebSocket endpoint"""
    return {
        "test_endpoint": "/ws/test",
        "description": "Simple test WebSocket for debugging connections",
        "usage": "Connect to ws://<host>:<port>/ws/test",
        "server_host": settings.host,
        "server_port": settings.port
    }


@app.get("/api/chat/statistics")
async def get_enhanced_chat_statistics(hours: int = 24):
    """Get enhanced chat statistics with detailed analysis"""
    if not chat_analyzer:
        # For development mode, return comprehensive mock data
        if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
            return {
                "total_messages": 256,
                "categories": {
                    "disaster": 42,
                    "product": 28,
                    "question": 67,
                    "greeting": 35,
                    "general": 84
                },
                "average_sentiment": 0.65,
                "unique_users": 89,
                "super_chat_count": 8,
                "super_chat_total": 12500.0,
                "top_keywords": [
                    ["地震", 25], ["防災", 18], ["津波", 15], ["備え", 12], ["安全", 10],
                    ["earthquake", 8], ["emergency", 7], ["準備", 6], ["情報", 5], ["助かる", 4]
                ],
                "auto_responses_sent": 23,
                "period_hours": hours,
                "session_statistics": {
                    "session_start": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "session_messages": 67,
                    "session_disaster_mentions": 12,
                    "session_product_mentions": 8,
                    "session_auto_responses": 5
                },
                "is_live": True
            }
        else:
            raise HTTPException(status_code=503, detail="Chat analyzer not available")
    
    try:
        # Get comprehensive statistics from the enhanced chat analyzer
        stats = chat_analyzer.get_chat_statistics(hours)
        logger.info(f"Retrieved enhanced chat statistics for last {hours} hours")
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching enhanced chat statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch enhanced statistics")


@app.get("/api/chat/live-status")
async def get_chat_live_status():
    """Get current live chat monitoring status"""
    if not chat_analyzer:
        return {
            "is_monitoring": False,
            "video_id": "development_mode",
            "chat_available": False,
            "api_configured": False,
            "messages_processed": 0,
            "uptime": "N/A",
            "last_message_time": None
        }
    
    try:
        # Get current status from chat analyzer
        is_live = chat_analyzer.running and (chat_analyzer.chat.is_alive() if chat_analyzer.chat else False)
        
        return {
            "is_monitoring": chat_analyzer.running,
            "video_id": chat_analyzer.video_id,
            "chat_available": chat_analyzer.chat is not None,
            "api_configured": chat_analyzer.youtube_service is not None,
            "messages_processed": chat_analyzer.stats.get('total_messages', 0),
            "uptime": str(datetime.now() - chat_analyzer.stats.get('start_time', datetime.now())),
            "last_message_time": datetime.now().isoformat(),
            "is_live": is_live,
            "auto_responses_enabled": chat_analyzer.config.get('auto_response_enabled', False),
            "ai_responses_enabled": chat_analyzer.ai_enabled
        }
        
    except Exception as e:
        logger.error(f"Error getting chat live status: {e}")
        return {
            "is_monitoring": False,
            "video_id": "error",
            "chat_available": False,
            "api_configured": False,
            "messages_processed": 0,
            "uptime": "Error",
            "error": str(e)
        }


# P2P地震情報 API v2 Endpoints

@app.get("/api/p2p/history")
async def get_p2p_history(
    codes: Optional[str] = Query(None, description="情報コード (カンマ区切り)"),
    limit: int = Query(10, ge=1, le=100, description="返却件数"),
    offset: int = Query(0, ge=0, description="読み飛ばす件数")
):
    """P2P地震情報履歴データ取得"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        # Parse codes parameter
        codes_list = None
        if codes:
            codes_list = [int(code.strip()) for code in codes.split(',')]
        
        history_data = await p2p_earthquake_service.get_history(
            codes=codes_list,
            limit=limit,
            offset=offset
        )
        
        return {
            "data": [
                {
                    "id": item.id,
                    "code": item.code,
                    "time": item.time,
                    "type": type(item).__name__,
                    "content": item.dict()
                }
                for item in history_data
            ],
            "count": len(history_data),
            "limit": limit,
            "offset": offset,
            "total_available": "unknown"  # P2P API doesn't provide total count
        }
    except Exception as e:
        logger.error(f"Error fetching P2P history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch P2P history data")

@app.get("/api/p2p/jma/quakes")
async def get_p2p_jma_quakes(
    limit: int = Query(10, ge=1, le=100, description="返却件数"),
    offset: int = Query(0, ge=0, description="読み飛ばす件数"),
    order: int = Query(-1, description="並び順 (1: 昇順, -1: 降順)"),
    since_date: Optional[str] = Query(None, description="指定日以降 (yyyyMMdd)"),
    until_date: Optional[str] = Query(None, description="指定日以前 (yyyyMMdd)"),
    quake_type: Optional[str] = Query(None, description="地震情報の種類"),
    min_magnitude: Optional[float] = Query(None, description="マグニチュード下限"),
    max_magnitude: Optional[float] = Query(None, description="マグニチュード上限"),
    min_scale: Optional[int] = Query(None, description="最大震度下限"),
    max_scale: Optional[int] = Query(None, description="最大震度上限")
):
    """JMA地震情報リスト取得"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        jma_quakes = await p2p_earthquake_service.get_jma_quakes(
            limit=limit,
            offset=offset,
            order=order,
            since_date=since_date,
            until_date=until_date,
            quake_type=quake_type,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            min_scale=min_scale,
            max_scale=max_scale
        )
        
        return {
            "earthquakes": [
                {
                    "id": quake.id,
                    "code": quake.code,
                    "time": quake.time,
                    "issue": {
                        "source": quake.issue.source,
                        "time": quake.issue.time,
                        "type": quake.issue.type,
                        "correct": quake.issue.correct
                    },
                    "earthquake": {
                        "time": quake.earthquake.time,
                        "hypocenter": {
                            "name": quake.earthquake.hypocenter.name if quake.earthquake.hypocenter else None,
                            "latitude": quake.earthquake.hypocenter.latitude if quake.earthquake.hypocenter else None,
                            "longitude": quake.earthquake.hypocenter.longitude if quake.earthquake.hypocenter else None,
                            "depth": quake.earthquake.hypocenter.depth if quake.earthquake.hypocenter else None,
                            "magnitude": quake.earthquake.hypocenter.magnitude if quake.earthquake.hypocenter else None
                        } if quake.earthquake.hypocenter else None,
                        "maxScale": quake.earthquake.maxScale,
                        "maxScaleString": scale_int_to_string(quake.earthquake.maxScale) if quake.earthquake.maxScale and quake.earthquake.maxScale > 0 else "不明",
                        "domesticTsunami": quake.earthquake.domesticTsunami,
                        "foreignTsunami": quake.earthquake.foreignTsunami
                    },
                    "points": [
                        {
                            "pref": point.pref,
                            "addr": point.addr,
                            "isArea": point.isArea,
                            "scale": point.scale,
                            "scaleString": scale_int_to_string(point.scale)
                        }
                        for point in quake.points or []
                    ],
                    "comments": quake.comments.dict() if quake.comments else None
                }
                for quake in jma_quakes
            ],
            "count": len(jma_quakes),
            "parameters": {
                "limit": limit,
                "offset": offset,
                "order": order,
                "filters": {
                    "since_date": since_date,
                    "until_date": until_date,
                    "quake_type": quake_type,
                    "magnitude_range": f"{min_magnitude}-{max_magnitude}" if min_magnitude or max_magnitude else None,
                    "scale_range": f"{min_scale}-{max_scale}" if min_scale or max_scale else None
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching JMA quakes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch JMA earthquake data")

@app.get("/api/p2p/jma/quake/{quake_id}")
async def get_p2p_jma_quake_by_id(quake_id: str):
    """特定の地震情報取得"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        quake = await p2p_earthquake_service.get_jma_quake_by_id(quake_id)
        if not quake:
            raise HTTPException(status_code=404, detail="Earthquake information not found")
        
        return {
            "id": quake.id,
            "code": quake.code,
            "time": quake.time,
            "issue": quake.issue.dict(),
            "earthquake": quake.earthquake.dict(),
            "points": [point.dict() for point in quake.points or []],
            "comments": quake.comments.dict() if quake.comments else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quake by ID: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch earthquake information")

@app.get("/api/p2p/jma/tsunamis")
async def get_p2p_jma_tsunamis(
    limit: int = Query(10, ge=1, le=100, description="返却件数"),
    offset: int = Query(0, ge=0, description="読み飛ばす件数"),
    order: int = Query(-1, description="並び順 (1: 昇順, -1: 降順)"),
    since_date: Optional[str] = Query(None, description="指定日以降 (yyyyMMdd)"),
    until_date: Optional[str] = Query(None, description="指定日以前 (yyyyMMdd)")
):
    """JMA津波予報リスト取得"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        tsunamis = await p2p_earthquake_service.get_jma_tsunamis(
            limit=limit,
            offset=offset,
            order=order,
            since_date=since_date,
            until_date=until_date
        )
        
        return {
            "tsunamis": [
                {
                    "id": tsunami.id,
                    "code": tsunami.code,
                    "time": tsunami.time,
                    "cancelled": tsunami.cancelled,
                    "issue": tsunami.issue.dict(),
                    "areas": [
                        {
                            "grade": area.grade,
                            "immediate": area.immediate,
                            "name": area.name,
                            "firstHeight": area.firstHeight.dict() if area.firstHeight else None,
                            "maxHeight": area.maxHeight.dict() if area.maxHeight else None
                        }
                        for area in tsunami.areas
                    ]
                }
                for tsunami in tsunamis
            ],
            "count": len(tsunamis),
            "parameters": {
                "limit": limit,
                "offset": offset,
                "order": order,
                "filters": {
                    "since_date": since_date,
                    "until_date": until_date
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching JMA tsunamis: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch JMA tsunami data")

@app.get("/api/p2p/jma/tsunami/{tsunami_id}")
async def get_p2p_jma_tsunami_by_id(tsunami_id: str):
    """特定の津波予報取得"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        tsunami = await p2p_earthquake_service.get_jma_tsunami_by_id(tsunami_id)
        if not tsunami:
            raise HTTPException(status_code=404, detail="Tsunami information not found")
        
        return {
            "id": tsunami.id,
            "code": tsunami.code,
            "time": tsunami.time,
            "cancelled": tsunami.cancelled,
            "issue": tsunami.issue.dict(),
            "areas": [area.dict() for area in tsunami.areas]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tsunami by ID: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tsunami information")

@app.get("/api/p2p/earthquakes/latest")
async def get_p2p_latest_earthquakes(limit: int = Query(10, ge=1, le=50, description="返却件数")):
    """最新の地震情報取得 (WebSocket or HTTP API)"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        # First try to get data from WebSocket cache
        latest_earthquakes = p2p_earthquake_service.get_latest_earthquakes(limit)
        
        # If no WebSocket data, fetch from HTTP API
        if not latest_earthquakes:
            logger.info("No WebSocket data available, fetching from HTTP API")
            latest_earthquakes = await p2p_earthquake_service.get_jma_quakes(limit=limit)
        
        return {
            "earthquakes": [
                {
                    "id": quake.id,
                    "time": quake.time,
                    "location": quake.earthquake.hypocenter.name if quake.earthquake.hypocenter else "不明",
                    "magnitude": quake.earthquake.hypocenter.magnitude if quake.earthquake.hypocenter else None,
                    "depth": quake.earthquake.hypocenter.depth if quake.earthquake.hypocenter else None,
                    "latitude": quake.earthquake.hypocenter.latitude if quake.earthquake.hypocenter else None,
                    "longitude": quake.earthquake.hypocenter.longitude if quake.earthquake.hypocenter else None,
                    "maxScale": quake.earthquake.maxScale,
                    "maxScaleString": scale_int_to_string(quake.earthquake.maxScale) if quake.earthquake.maxScale and quake.earthquake.maxScale > 0 else "不明",
                    "tsunami": quake.earthquake.domesticTsunami != "None" if quake.earthquake.domesticTsunami else False,
                    "source": "P2P地震情報",
                    "issueType": quake.issue.type
                }
                for quake in latest_earthquakes
            ],
            "count": len(latest_earthquakes),
            "source": "P2P地震情報 HTTP API" if not p2p_earthquake_service.get_latest_earthquakes(1) else "P2P地震情報 WebSocket API",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching latest earthquakes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest earthquake data")

@app.get("/api/p2p/tsunamis/latest")
async def get_p2p_latest_tsunamis(limit: int = Query(10, ge=1, le=50, description="返却件数")):
    """最新の津波予報取得 (WebSocketから受信したデータ)"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        latest_tsunamis = p2p_earthquake_service.get_latest_tsunamis(limit)
        
        return {
            "tsunamis": [
                {
                    "id": tsunami.id,
                    "time": tsunami.time,
                    "cancelled": tsunami.cancelled,
                    "areas": [
                        {
                            "name": area.name,
                            "grade": area.grade,
                            "immediate": area.immediate,
                            "maxHeight": area.maxHeight.description if area.maxHeight else None
                        }
                        for area in tsunami.areas
                    ],
                    "source": "P2P地震情報"
                }
                for tsunami in latest_tsunamis
            ],
            "count": len(latest_tsunamis),
            "source": "P2P地震情報 WebSocket API",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching latest tsunamis: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest tsunami data")

@app.get("/api/p2p/eew/latest")
async def get_p2p_latest_eew(limit: int = Query(10, ge=1, le=50, description="返却件数")):
    """最新の緊急地震速報取得 (WebSocketから受信したデータ)"""
    if not p2p_earthquake_service:
        raise HTTPException(status_code=503, detail="P2P earthquake service not available")
    
    try:
        latest_eew = p2p_earthquake_service.get_latest_eew(limit)
        
        return {
            "eew": [
                {
                    "id": eew.id,
                    "time": eew.time,
                    "eventId": eew.issue.eventId,
                    "serial": eew.issue.serial,
                    "cancelled": eew.cancelled,
                    "test": eew.test or False,
                    "earthquake": {
                        "location": eew.earthquake.hypocenter.name if eew.earthquake and eew.earthquake.hypocenter else None,
                        "magnitude": eew.earthquake.hypocenter.magnitude if eew.earthquake and eew.earthquake.hypocenter else None,
                        "latitude": eew.earthquake.hypocenter.latitude if eew.earthquake and eew.earthquake.hypocenter else None,
                        "longitude": eew.earthquake.hypocenter.longitude if eew.earthquake and eew.earthquake.hypocenter else None,
                        "depth": eew.earthquake.hypocenter.depth if eew.earthquake and eew.earthquake.hypocenter else None,
                        "originTime": eew.earthquake.originTime if eew.earthquake else None,
                        "arrivalTime": eew.earthquake.arrivalTime if eew.earthquake else None
                    } if eew.earthquake else None,
                    "areas": [
                        {
                            "pref": area.pref,
                            "name": area.name,
                            "scaleFrom": area.scaleFrom,
                            "scaleTo": area.scaleTo,
                            "kindCode": area.kindCode,
                            "arrivalTime": area.arrivalTime
                        }
                        for area in eew.areas or []
                    ],
                    "source": "P2P地震情報"
                }
                for eew in latest_eew
            ],
            "count": len(latest_eew),
            "source": "P2P地震情報 WebSocket API",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching latest EEW: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest EEW data")

@app.get("/api/p2p/status")
async def get_p2p_service_status():
    """P2P地震情報サービス状態取得"""
    if not p2p_earthquake_service:
        return {
            "service_available": False,
            "error": "P2P earthquake service not initialized"
        }
    
    try:
        status = p2p_earthquake_service.get_service_status()
        return {
            "service_available": True,
            "websocket_monitoring": status['is_monitoring'],
            "websocket_connected": status['websocket_connected'],
            "environment": "sandbox" if status['use_sandbox'] else "production",
            "api_endpoints": {
                "base_url": status['base_url'],
                "websocket_url": status['ws_url']
            },
            "data_status": {
                "latest_data_types": status['latest_data_count'],
                "history_items": status['history_count'],
                "registered_callbacks": status['registered_callbacks']
            },
            "rate_limits": {
                "history_api": "60 requests/minute",
                "jma_api": "10 requests/minute",
                "websocket": "Real-time"
            },
            "information_codes": {
                "551": "地震情報",
                "552": "津波予報", 
                "554": "緊急地震速報発表検出",
                "555": "各地域ピア数",
                "556": "緊急地震速報（警報）",
                "561": "地震感知情報",
                "9611": "地震感知情報解析結果"
            },
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting P2P service status: {e}")
        return {
            "service_available": False,
            "error": str(e)
        }

@app.get("/api/seismic/stations")
async def get_seismic_stations():
    """Get seismic station data with intensity information from recent earthquakes"""
    if not p2p_earthquake_service:
        # Return default stations if service not available
        logger.warning("P2P earthquake service not available, returning default stations")
        default_stations = [
            {"id": "1", "name": "北海道", "location": "釧路", "prefecture": "北海道", "intensity": 0, "latitude": 42.9849, "longitude": 144.3819},
            {"id": "2", "name": "北海道", "location": "苫小牧", "prefecture": "北海道", "intensity": 0, "latitude": 42.6343, "longitude": 141.6059},
            {"id": "3", "name": "新潟県", "location": "新潟", "prefecture": "新潟県", "intensity": 0, "latitude": 37.9161, "longitude": 139.0364},
            {"id": "4", "name": "石川県", "location": "正院", "prefecture": "石川県", "intensity": 0, "latitude": 37.4479, "longitude": 137.2778},
            {"id": "5", "name": "埼玉県", "location": "岩槻", "prefecture": "埼玉県", "intensity": 0, "latitude": 35.9494, "longitude": 139.6946},
            {"id": "6", "name": "東京都", "location": "新宿", "prefecture": "東京都", "intensity": 0, "latitude": 35.6896, "longitude": 139.6917},
            {"id": "7", "name": "神奈川県", "location": "相模原", "prefecture": "神奈川県", "intensity": 0, "latitude": 35.5707, "longitude": 139.3683},
            {"id": "8", "name": "大阪府", "location": "堺", "prefecture": "大阪府", "intensity": 0, "latitude": 34.5733, "longitude": 135.4828},
            {"id": "9", "name": "宮崎県", "location": "都城", "prefecture": "宮崎県", "intensity": 0, "latitude": 31.7190, "longitude": 131.0619},
            {"id": "10", "name": "沖縄県", "location": "名護", "prefecture": "沖縄県", "intensity": 0, "latitude": 26.5917, "longitude": 127.9769},
        ]
        return {"stations": default_stations, "lastUpdate": datetime.now().isoformat(), "source": "default"}
    
    try:
        # Get recent earthquake with detailed scale information
        quakes = await p2p_earthquake_service.get_jma_quakes(limit=1, order=-1, quake_type="DetailScale")
        
        if quakes and len(quakes) > 0:
            latest_quake = quakes[0]
            
            # Extract observation points
            if hasattr(latest_quake, 'points') and latest_quake.points:
                stations = []
                for idx, point in enumerate(latest_quake.points[:50]):  # Limit to 50 stations
                    stations.append({
                        "id": str(idx + 1),
                        "name": point.pref,
                        "location": point.addr,
                        "prefecture": point.pref,
                        "intensity": point.scale / 10.0,  # Convert to seismic intensity (震度)
                        "isArea": point.isArea,
                        "earthquakeId": latest_quake.id if hasattr(latest_quake, 'id') else None,
                        "earthquakeTime": latest_quake.earthquake.time if hasattr(latest_quake, 'earthquake') else None,
                    })
                
                return {
                    "stations": stations,
                    "lastUpdate": datetime.now().isoformat(),
                    "source": "p2p_earthquake",
                    "earthquake": {
                        "id": latest_quake.id if hasattr(latest_quake, 'id') else None,
                        "time": latest_quake.earthquake.time if hasattr(latest_quake, 'earthquake') else None,
                        "maxScale": latest_quake.earthquake.maxScale / 10.0 if hasattr(latest_quake, 'earthquake') and latest_quake.earthquake.maxScale else None,
                        "hypocenter": {
                            "name": latest_quake.earthquake.hypocenter.name if hasattr(latest_quake, 'earthquake') and latest_quake.earthquake.hypocenter else None,
                            "magnitude": latest_quake.earthquake.hypocenter.magnitude if hasattr(latest_quake, 'earthquake') and latest_quake.earthquake.hypocenter else None,
                        } if hasattr(latest_quake, 'earthquake') and latest_quake.earthquake.hypocenter else None
                    }
                }
        
        # If no detailed earthquake data, return default stations
        default_stations = [
            {"id": "1", "name": "北海道", "location": "釧路", "prefecture": "北海道", "intensity": 0, "latitude": 42.9849, "longitude": 144.3819},
            {"id": "2", "name": "北海道", "location": "苫小牧", "prefecture": "北海道", "intensity": 0, "latitude": 42.6343, "longitude": 141.6059},
            {"id": "3", "name": "新潟県", "location": "新潟", "prefecture": "新潟県", "intensity": 0, "latitude": 37.9161, "longitude": 139.0364},
            {"id": "4", "name": "石川県", "location": "正院", "prefecture": "石川県", "intensity": 0, "latitude": 37.4479, "longitude": 137.2778},
            {"id": "5", "name": "埼玉県", "location": "岩槻", "prefecture": "埼玉県", "intensity": 0, "latitude": 35.9494, "longitude": 139.6946},
            {"id": "6", "name": "東京都", "location": "新宿", "prefecture": "東京都", "intensity": 0, "latitude": 35.6896, "longitude": 139.6917},
            {"id": "7", "name": "神奈川県", "location": "相模原", "prefecture": "神奈川県", "intensity": 0, "latitude": 35.5707, "longitude": 139.3683},
            {"id": "8", "name": "大阪府", "location": "堺", "prefecture": "大阪府", "intensity": 0, "latitude": 34.5733, "longitude": 135.4828},
            {"id": "9", "name": "宮崎県", "location": "都城", "prefecture": "宮崎県", "intensity": 0, "latitude": 31.7190, "longitude": 131.0619},
            {"id": "10", "name": "沖縄県", "location": "名護", "prefecture": "沖縄県", "intensity": 0, "latitude": 26.5917, "longitude": 127.9769},
        ]
        return {"stations": default_stations, "lastUpdate": datetime.now().isoformat(), "source": "default"}
        
    except Exception as e:
        logger.error(f"Error fetching seismic station data: {e}")
        # Return default stations on error
        default_stations = [
            {"id": "1", "name": "北海道", "location": "釧路", "prefecture": "北海道", "intensity": 0, "latitude": 42.9849, "longitude": 144.3819},
            {"id": "2", "name": "北海道", "location": "苫小牧", "prefecture": "北海道", "intensity": 0, "latitude": 42.6343, "longitude": 141.6059},
            {"id": "3", "name": "新潟県", "location": "新潟", "prefecture": "新潟県", "intensity": 0, "latitude": 37.9161, "longitude": 139.0364},
            {"id": "4", "name": "石川県", "location": "正院", "prefecture": "石川県", "intensity": 0, "latitude": 37.4479, "longitude": 137.2778},
            {"id": "5", "name": "埼玉県", "location": "岩槻", "prefecture": "埼玉県", "intensity": 0, "latitude": 35.9494, "longitude": 139.6946},
            {"id": "6", "name": "東京都", "location": "新宿", "prefecture": "東京都", "intensity": 0, "latitude": 35.6896, "longitude": 139.6917},
            {"id": "7", "name": "神奈川県", "location": "相模原", "prefecture": "神奈川県", "intensity": 0, "latitude": 35.5707, "longitude": 139.3683},
            {"id": "8", "name": "大阪府", "location": "堺", "prefecture": "大阪府", "intensity": 0, "latitude": 34.5733, "longitude": 135.4828},
            {"id": "9", "name": "宮崎県", "location": "都城", "prefecture": "宮崎県", "intensity": 0, "latitude": 31.7190, "longitude": 131.0619},
            {"id": "10", "name": "沖縄県", "location": "名護", "prefecture": "沖縄県", "intensity": 0, "latitude": 26.5917, "longitude": 127.9769},
        ]
        return {"stations": default_stations, "lastUpdate": datetime.now().isoformat(), "source": "default", "error": str(e)}

@app.get("/api/seismic/waveform")
async def get_seismic_waveform_data():
    """Get real-time seismic waveform data based on recent earthquake activity
    
    Returns simulated waveform data for 10 seismic stations across Japan.
    The waveforms are influenced by recent earthquake events from P2P API.
    """
    import math
    
    # Define monitoring stations
    stations = [
        {"id": "1", "name": "北海道", "location": "釧路支庁釧路", "lat": 42.98, "lng": 144.38},
        {"id": "2", "name": "北海道", "location": "胆振支庁苫小牧", "lat": 42.63, "lng": 141.60},
        {"id": "3", "name": "新潟県", "location": "新潟", "lat": 37.90, "lng": 139.02},
        {"id": "4", "name": "石川県", "location": "正院", "lat": 37.47, "lng": 137.26},
        {"id": "5", "name": "埼玉県", "location": "岩槻", "lat": 35.94, "lng": 139.69},
        {"id": "6", "name": "東京都", "location": "新宿", "lat": 35.69, "lng": 139.70},
        {"id": "7", "name": "神奈川県", "location": "相模原", "lat": 35.55, "lng": 139.37},
        {"id": "8", "name": "大阪府", "location": "堺", "lat": 34.57, "lng": 135.47},
        {"id": "9", "name": "宮崎県", "location": "都城", "lat": 31.72, "lng": 131.06},
        {"id": "10", "name": "沖縄県", "location": "名護", "lat": 26.59, "lng": 127.97},
    ]
    
    # Get recent earthquakes to influence waveforms
    recent_earthquakes = []
    if p2p_earthquake_service:
        try:
            latest_quakes = p2p_earthquake_service.get_latest_earthquakes(5)
            for quake in latest_quakes:
                if hasattr(quake, 'earthquake') and quake.earthquake and quake.earthquake.hypocenter:
                    hypo = quake.earthquake.hypocenter
                    if hypo.latitude and hypo.longitude and hypo.magnitude:
                        recent_earthquakes.append({
                            "lat": hypo.latitude,
                            "lng": hypo.longitude,
                            "magnitude": hypo.magnitude,
                            "depth": hypo.depth or 10,
                            "time": quake.time
                        })
        except Exception as e:
            logger.warning(f"Could not fetch recent earthquakes for waveforms: {e}")
    
    # Calculate distance between two coordinates (simplified)
    def calculate_distance(lat1, lng1, lat2, lng2):
        """Calculate approximate distance in km using simple formula"""
        lat_diff = (lat2 - lat1) * 111  # 1 degree latitude ≈ 111 km
        lng_diff = (lng2 - lng1) * 111 * math.cos(math.radians(lat1))
        return math.sqrt(lat_diff**2 + lng_diff**2)
    
    # Generate waveform data for each station
    station_data = []
    current_time = datetime.now()
    
    for station in stations:
        # Base noise level
        base_amplitude = random.uniform(0.1, 0.3)
        
        # Calculate influence from recent earthquakes
        earthquake_influence = 0.0
        for eq in recent_earthquakes:
            distance = calculate_distance(
                station["lat"], station["lng"],
                eq["lat"], eq["lng"]
            )
            
            # Calculate influence based on magnitude and distance
            if distance > 0:
                # Influence decreases with distance, increases with magnitude
                influence = (eq["magnitude"] / max(distance, 1)) * 5
                earthquake_influence += min(influence, 2.0)  # Cap influence
        
        # Generate 100 data points for the waveform
        waveform_data = []
        for i in range(100):
            # Base waveform (noise)
            noise = random.uniform(-base_amplitude, base_amplitude)
            
            # Periodic component (simulating natural oscillation)
            time_factor = (current_time.timestamp() + i * 0.05)  # 50ms intervals
            periodic = math.sin(time_factor + int(station["id"]) * math.pi / 5) * 0.2
            
            # Add earthquake influence
            eq_wave = earthquake_influence * math.sin(time_factor * 2) * 0.3
            
            # Occasional spikes
            spike = 0
            if random.random() > 0.97:
                spike = random.uniform(-0.5, 0.5)
            
            # Combine all components
            value = noise + periodic + eq_wave + spike
            waveform_data.append(round(value, 4))
        
        station_data.append({
            "id": station["id"],
            "name": station["name"],
            "location": station["location"],
            "latitude": station["lat"],
            "longitude": station["lng"],
            "waveform": waveform_data,
            "current_amplitude": round(abs(waveform_data[-1]), 4),
            "max_amplitude": round(max([abs(x) for x in waveform_data]), 4),
            "earthquake_influence": round(earthquake_influence, 2)
        })
    
    return {
        "stations": station_data,
        "timestamp": current_time.isoformat(),
        "recent_earthquakes_count": len(recent_earthquakes),
        "update_interval_ms": 50,
        "data_points_per_station": 100,
        "unit": "gal"
    }

# Social Media Automation API Endpoints
@app.get("/api/social-media/status")
async def get_social_media_status():
    """Get social media automation service status"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        status = await social_media_automation.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting social media status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get social media status")

@app.get("/api/social-media/history")
async def get_social_media_history(hours: int = 24):
    """Get social media post history"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        history = await social_media_automation.get_post_history(hours)
        return {
            "posts": history,
            "total_posts": len(history),
            "hours": hours
        }
    except Exception as e:
        logger.error(f"Error getting social media history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get social media history")

@app.post("/api/social-media/emergency-alert")
async def post_emergency_alert(request: dict):
    """Post emergency alert to all configured social media channels"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        disaster_type = request.get('disaster_type', 'unknown')
        disaster_data = request.get('disaster_data', {})
        
        channel_ids = request.get('channel_ids')
        post_ids = await social_media_automation.post_emergency_alert(disaster_type, disaster_data, channel_ids=channel_ids)
        
        return {
            "success": True,
            "post_ids": post_ids,
            "total_posts": len(post_ids),
            "disaster_type": disaster_type
        }
    except Exception as e:
        logger.error(f"Error posting emergency alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to post emergency alert")

@app.post("/api/social-media/situation-update")
async def post_situation_update(request: dict):
    """Post situation update to social media channels"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        situation_data = request.get('situation_data', {})
        
        channel_ids = request.get('channel_ids')
        post_ids = await social_media_automation.post_situation_update(situation_data, channel_ids=channel_ids)
        
        return {
            "success": True,
            "post_ids": post_ids,
            "total_posts": len(post_ids)
        }
    except Exception as e:
        logger.error(f"Error posting situation update: {e}")
        raise HTTPException(status_code=500, detail="Failed to post situation update")

@app.post("/api/social-media/evacuation-order")
async def post_evacuation_order(request: dict):
    """Post evacuation order to social media channels"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        evacuation_data = request.get('evacuation_data', {})
        
        channel_ids = request.get('channel_ids')
        post_ids = await social_media_automation.post_evacuation_order(evacuation_data, channel_ids=channel_ids)
        
        return {
            "success": True,
            "post_ids": post_ids,
            "total_posts": len(post_ids)
        }
    except Exception as e:
        logger.error(f"Error posting evacuation order: {e}")
        raise HTTPException(status_code=500, detail="Failed to post evacuation order")

@app.get("/api/social-media/channels")
async def get_social_media_channels():
    """Get list of configured social media channels"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        channels = []
        for channel_id, channel in social_media_automation.channels.items():
            channels.append({
                "channel_id": channel_id,
                "channel_name": channel.channel_name,
                "platform": channel.platform.value,
                "is_active": channel.is_active,
                "auto_posting": channel.auto_posting,
                "auto_commenting": channel.auto_commenting,
                "posting_frequency": channel.posting_frequency,
                "commenting_frequency": channel.commenting_frequency,
                "disaster_types": channel.disaster_types,
                "language": channel.language
            })
        
        return {
            "channels": channels,
            "total_channels": len(channels)
        }
    except Exception as e:
        logger.error(f"Error getting social media channels: {e}")
        raise HTTPException(status_code=500, detail="Failed to get social media channels")

@app.post("/api/social-media/test-post")
async def test_social_media_post(request: dict):
    """Test posting to social media channels"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    
    try:
        test_data = {
            "type": "test",
            "location": "テスト地域",
            "magnitude": "4.5",
            "intensity": "4",
            "message": "This is a test emergency alert"
        }
        
        post_ids = await social_media_automation.post_emergency_alert("test", test_data)
        
        return {
            "success": True,
            "post_ids": post_ids,
            "total_posts": len(post_ids),
            "test_data": test_data
        }
    except Exception as e:
        logger.error(f"Error testing social media post: {e}")
        raise HTTPException(status_code=500, detail="Failed to test social media post")

@app.get("/api/social-media/schedules")
async def list_social_media_schedules():
    """List recurring social media jobs"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    try:
        schedules = await social_media_automation.list_recurring_jobs()
        return {"schedules": schedules, "total": len(schedules)}
    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to list schedules")

@app.post("/api/social-media/schedules")
async def create_social_media_schedule(request: dict):
    """Create a recurring job for automatic posting/commenting
    Body example:
    {
      "channel_ids": ["line_disaster_info", "youtube_live_emergency"],
      "mode": "self_post" | "comment",
      "post_type": "emergency_alert" | "situation_update" | "evacuation_order",
      "frequency_minutes": 15,
      "targets": ["<yt_video_or_chat_id>"] ,
      "content": { ... },
      "enabled": true
    }
    """
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    try:
        channel_ids = request.get("channel_ids", [])
        mode = request.get("mode", "self_post")
        post_type_str = request.get("post_type", "situation_update")
        frequency_minutes = int(request.get("frequency_minutes", 30))
        targets = request.get("targets")
        content = request.get("content")
        enabled = bool(request.get("enabled", True))

        if not channel_ids:
            raise HTTPException(status_code=400, detail="channel_ids is required and must be non-empty")

        try:
            post_type = PostType(post_type_str)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid post_type")

        job_id = await social_media_automation.create_recurring_job(
            channel_ids=channel_ids,
            mode=mode,
            post_type=post_type,
            frequency_minutes=frequency_minutes,
            targets=targets,
            content=content,
            enabled=enabled
        )
        return {"job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")

@app.patch("/api/social-media/schedules/{job_id}")
async def update_social_media_schedule(job_id: str, request: dict):
    """Update an existing schedule"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    try:
        updates = dict(request or {})
        # Accept string post_type
        if "post_type" in updates:
            try:
                updates["post_type"] = PostType(updates["post_type"])
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid post_type")
        ok = await social_media_automation.update_recurring_job(job_id, updates)
        if not ok:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"updated": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update schedule")

@app.delete("/api/social-media/schedules/{job_id}")
async def delete_social_media_schedule(job_id: str):
    """Delete a schedule"""
    if not social_media_automation:
        raise HTTPException(status_code=503, detail="Social media automation service not available")
    try:
        ok = await social_media_automation.delete_recurring_job(job_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete schedule")

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 