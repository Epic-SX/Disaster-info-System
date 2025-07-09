#!/usr/bin/env python3
"""
Main FastAPI server for the Disaster Information System backend.
Provides REST APIs for disaster data, YouTube chat integration, and social media automation.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
import json # Added for json.loads
import httpx

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from youtube_chat_service import YouTubeChatAnalyzer
from youtube_search_service import YouTubeSearchService, YouTubeVideo, YouTubeSearchResult
from disaster_api_service import DisasterAPIService, EarthquakeInfo, TsunamiInfo, DisasterAlert as DisasterAlertNew


class Settings(BaseSettings):
    """Application settings from environment variables"""
    debug: bool = True
    port: int = 8000
    host: str = "localhost"
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
    openai_api_key: str = "sk-mock-key-for-development"
    youtube_api_key: str = "mock-youtube-api-key"
    youtube_channel_id: str = "mock-channel-id"
    youtube_live_chat_id: str = "mock-chat-id"
    
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
        extra = "allow"  # Allow extra fields for development flexibility


# Global variables
settings = Settings()
chat_analyzer: Optional[YouTubeChatAnalyzer] = None
youtube_search_service: Optional[YouTubeSearchService] = None
disaster_api_service: Optional[DisasterAPIService] = None
connected_websockets: List[WebSocket] = []

# Add missing global variables
chat_messages: List[dict] = []
active_connections: List[WebSocket] = []

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    global chat_analyzer, youtube_search_service, disaster_api_service
    
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
        
        # Start real-time earthquake monitoring in background
        asyncio.create_task(disaster_api_service.start_realtime_monitoring())
        logger.info("✓ Real-time disaster monitoring started")
    except Exception as e:
        logger.error(f"Failed to initialize disaster API service: {e}")
        disaster_api_service = None
    
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
    
    yield
    
    # Shutdown
    logger.info("Shutting down Disaster Information System backend...")
    if chat_analyzer:
        if hasattr(chat_analyzer, 'stop_monitoring'):
            chat_analyzer.stop_monitoring()
    
    if disaster_api_service and disaster_api_service.iij_websocket:
        await disaster_api_service.iij_websocket.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Disaster Information System API",
    description="Backend API for real-time disaster information, YouTube chat integration, and social media automation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background task for monitoring chat
async def monitor_chat():
    """Background task to monitor YouTube live chat"""
    if not chat_analyzer:
        return
    
    try:
        await chat_analyzer.start_monitoring()
    except Exception as e:
        logger.error(f"Chat monitoring error: {e}")


# Helper function to get wind data
async def get_current_wind_data():
    """Get current wind data for WebSocket updates"""
    try:
        # Same logic as the API endpoint but without HTTP response
        API_KEY = "demo_key"  # Replace with actual API key
        
        cities = [
            {"name": "東京", "lat": 35.6762, "lon": 139.6503},
            {"name": "大阪", "lat": 34.6937, "lon": 135.5023},
            {"name": "横浜", "lat": 35.4437, "lon": 139.6380}
        ]
        
        wind_data = []
        
        async with httpx.AsyncClient() as client:
            for city in cities:
                try:
                    # Return enhanced mock data with more realistic values
                    import random
                    base_speed = random.randint(5, 25)
                    gusts = base_speed + random.randint(5, 15)
                    directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
                    direction = random.choice(directions)
                    
                    # Determine status based on wind speed
                    if base_speed < 10:
                        status = "calm"
                    elif base_speed < 20:
                        status = "normal"
                    else:
                        status = "moderate"
                    
                    wind_data.append({
                        "location": city["name"],
                        "speed": f"{base_speed} km/h",
                        "direction": direction,
                        "gusts": f"{gusts} km/h",
                        "status": status,
                        "timestamp": datetime.now().isoformat(),
                        "temperature": f"{random.randint(15, 30)}°C",
                        "humidity": f"{random.randint(40, 80)}%"
                    })
                            
                except Exception as e:
                    logger.error(f"Error fetching weather data for {city['name']}: {e}")
                    # Fallback to mock data for this city
                    wind_data.append({
                        "location": city["name"],
                        "speed": "-- km/h",
                        "direction": "--",
                        "gusts": "-- km/h", 
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "temperature": "--°C",
                        "humidity": "--%"
                    })
        
        return wind_data
        
    except Exception as e:
        logger.error(f"Error getting wind data for WebSocket: {e}")
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
        initial_wind_data = await get_current_wind_data()
        await websocket.send_json({
            "type": "wind_data_update",
            "wind_data": initial_wind_data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Start background task to send periodic updates
        async def send_periodic_updates():
            while True:
                try:
                    # Send periodic analytics updates
                    analytics_data = {
                        "type": "analytics_update",
                        "data": {
                            "timestamp": datetime.now().isoformat(),
                            "total_messages": len(chat_messages),
                            "active_connections": len(connected_websockets),  # Use connected_websockets instead of active_connections
                            "uptime": datetime.now().isoformat()
                        }
                    }
                    await broadcast_to_websockets(analytics_data)
                    
                    # Send ping to keep connection alive
                    ping_data = {
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    }
                    await broadcast_to_websockets(ping_data)
                    
                    # Send real-time wind data updates every 10 seconds
                    try:
                        wind_data = await get_current_wind_data()
                        wind_update = {
                            "type": "wind_data_update",
                            "wind_data": wind_data,
                            "timestamp": datetime.now().isoformat()
                        }
                        await broadcast_to_websockets(wind_update)
                        logger.info(f"Sent wind data update with {len(wind_data)} locations")
                    except Exception as e:
                        logger.error(f"Error sending wind data updates: {e}")
                    
                    # Send earthquake data updates every 10 seconds (changed from 30 seconds)
                    try:
                        # Always generate mock data for now since we don't have real API access
                        import random
                        
                        # Generate more dynamic mock earthquake data
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
                            
                            mock_earthquakes.append({
                                "id": f"mock_eq_{i+1}_{int(datetime.now().timestamp())}",
                                "time": (datetime.now() - timedelta(hours=hours_ago)).isoformat(),
                                "location": location["name"],
                                "magnitude": magnitude,
                                "depth": depth,
                                "latitude": location["lat"] + random.uniform(-0.1, 0.1),
                                "longitude": location["lon"] + random.uniform(-0.1, 0.1),
                                "intensity": random.choice(intensities),
                                "tsunami": magnitude > 5.5 and random.choice([True, False])
                            })
                        
                        # Sort by time (most recent first)
                        mock_earthquakes.sort(key=lambda x: x["time"], reverse=True)
                        earthquake_data = mock_earthquakes[:6]  # Limit to 6 most recent
                        
                        earthquake_update = {
                            "type": "earthquake_update",
                            "data": earthquake_data,
                            "timestamp": datetime.now().isoformat()
                        }
                        await broadcast_to_websockets(earthquake_update)
                        logger.info(f"Sent earthquake update with {len(earthquake_data)} earthquakes")
                        
                    except Exception as e:
                        logger.error(f"Error sending earthquake updates: {e}")
                    
                    await asyncio.sleep(10)  # Send updates every 10 seconds
                except Exception as e:
                    logger.error(f"Error in periodic updates: {e}")
                    await asyncio.sleep(10)
        
        # Start the periodic updates task
        update_task = asyncio.create_task(send_periodic_updates())
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.info(f"Received WebSocket message: {message}")
                
                # Echo the message back or handle it
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
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
        except Exception:
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


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
            "disaster_apis": disaster_api_service is not None
        },
        "endpoints": {
            "health": "/api/health",
            "disasters": "/api/disasters",
            "earthquakes": "/api/earthquakes",
            "earthquakes_comprehensive": "/api/disasters/earthquakes/comprehensive",
            "tsunami_alerts": "/api/disasters/tsunami",
            "recent_alerts": "/api/disasters/alerts/recent",
            "seismic_hazard": "/api/disasters/seismic-hazard",
            "news": "/api/news",
            "chat": "/api/chat",
            "analytics": "/api/analytics",
            "youtube_search": "/api/youtube/search",
            "youtube_live_streams": "/api/youtube/live-streams",
            "youtube_trending": "/api/youtube/trending",
            "websocket": "/ws"
        },
        "api_sources": {
            "earthquake_data": ["P2P地震情報", "USGS", "IIJ Engineering"],
            "tsunami_alerts": ["P2P地震情報", "JMA"],
            "youtube_search": ["SerpApi"],
            "seismic_hazard": ["J-SHIS"],
            "real_time_monitoring": ["IIJ WebSocket"]
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
            "websocket_connections": len(connected_websockets)
        }
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


@app.get("/api/news", response_model=List[NewsArticle])
async def get_news_articles():
    """Get recent disaster-related news articles"""
    try:
        # This would integrate with news APIs
        articles = [
            NewsArticle(
                id="news_001",
                title="Emergency Preparedness Guidelines Updated",
                summary="New guidelines for disaster preparedness have been released by the government.",
                url="https://example.com/news/001",
                published_at=datetime.now(),
                category="emergency",
                source="NHK"
            )
        ]
        return articles
    except Exception as e:
        logger.error(f"Error fetching news articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news articles")


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
    """Get recent YouTube chat messages"""
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
                    "platform": "youtube"
                },
                {
                    "id": "msg_002", 
                    "message_id": "msg_002",
                    "author": "DisasterWatcher",
                    "message": "Please tell me about earthquake preparedness",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.1,
                    "category": "disaster",
                    "platform": "youtube"
                },
                {
                    "id": "msg_003",
                    "message_id": "msg_003", 
                    "author": "PreparedCitizen",
                    "message": "Where can I buy disaster supplies?",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_score": 0.5,
                    "category": "product",
                    "platform": "youtube"
                }
            ]
            return mock_messages[:limit]
        
        # Check for chat analyzer only after development mode check
        if not chat_analyzer:
            raise HTTPException(status_code=503, detail="Chat analyzer not available")
        
        # Real implementation would go here
        return []
    except Exception as e:
        logger.error(f"Error fetching chat messages: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat messages: {str(e)}")


@app.get("/api/chat/analytics", response_model=ChatAnalytics)
async def get_chat_analytics():
    """Get YouTube chat analytics"""
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
        # Real implementation would go here
        return ChatAnalytics(
            total_messages=0,
            disaster_mentions=0,
            product_mentions=0,
            sentiment_score=0.0,
            top_keywords=[],
            active_users=0
        )
    except Exception as e:
        logger.error(f"Error fetching chat analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat analytics")


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
    """Get configured auto-responses"""
    if not chat_analyzer:
        raise HTTPException(status_code=503, detail="Chat analyzer not available")
    
    # For development mode, return mock data
    if os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'development_mode') == 'development_mode':
        mock_responses = [
            AutoResponse(
                id=1,
                trigger_keywords="地震,earthquake", 
                response_text="🚨 地震情報を確認中です。最新情報は画面左上の地震情報パネルをご覧ください。",
                response_type="disaster",
                used_count=15,
                last_used_at=datetime.now().isoformat()
            ),
            AutoResponse(
                id=2,
                trigger_keywords="防災グッズ,disaster kit",
                response_text="🎒 おすすめの防災グッズ情報はこちら: https://example.com/disaster-kit",
                response_type="product",
                used_count=8,
                last_used_at=datetime.now().isoformat()
            )
        ]
        return mock_responses
    
    try:
        # Real implementation would go here
        return []
    except Exception as e:
        logger.error(f"Error fetching auto-responses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auto-responses")


# New YouTube Search API Endpoints
@app.get("/api/youtube/search")
async def search_youtube_videos(query: str = None, limit: int = 10):
    """Search for disaster-related YouTube videos"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_disaster_videos(query, limit)
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
                    "link": video.link
                }
                for video in result.videos
            ],
            "total_results": result.total_results,
            "search_query": result.search_query,
            "next_page_token": result.next_page_token
        }
    except Exception as e:
        logger.error(f"Error searching YouTube videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to search YouTube videos")


@app.get("/api/youtube/live-streams")
async def get_live_disaster_streams():
    """Get live disaster-related YouTube streams"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        result = await youtube_search_service.search_live_disaster_streams()
        return {
            "streams": [
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "channel": video.channel,
                    "thumbnail": video.thumbnail,
                    "link": video.link,
                    "duration": "LIVE"
                }
                for video in result.videos
            ],
            "total_results": result.total_results
        }
    except Exception as e:
        logger.error(f"Error fetching live streams: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch live streams")


@app.get("/api/youtube/trending")
async def get_trending_disaster_topics():
    """Get trending disaster-related topics on YouTube"""
    if not youtube_search_service:
        raise HTTPException(status_code=503, detail="YouTube search service not available")
    
    try:
        topics = await youtube_search_service.get_trending_disaster_topics()
        return {"trending_topics": topics}
    except Exception as e:
        logger.error(f"Error fetching trending topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending topics")


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
        earthquakes = await disaster_api_service.get_comprehensive_earthquake_data()
        
        # Add mock data for demonstration if no real data available
        if not earthquakes:
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
                    "time": (datetime.now() - timedelta(days=1)).isoformat(),
                    "location": "福島県沖",
                    "magnitude": 6.1,
                    "depth": 40,
                    "latitude": 37.7503,
                    "longitude": 141.4676,
                    "intensity": "5+",
                    "tsunami": True
                },
                {
                    "id": "mock_eq_5",
                    "time": (datetime.now() - timedelta(days=2)).isoformat(),
                    "location": "熊本県熊本地方",
                    "magnitude": 4.2,
                    "depth": 15,
                    "latitude": 32.7898,
                    "longitude": 130.7417,
                    "intensity": "4",
                    "tsunami": False
                }
            ]
            return mock_earthquakes
        
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
                "intensity": eq.intensity or "不明",
                "tsunami": eq.tsunami_warning
            }
            for eq in earthquakes
        ]
        
        return formatted_earthquakes
        
    except Exception as e:
        logger.error(f"Error fetching recent earthquake data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent earthquake data")

@app.get("/api/tsunami/alerts")
async def get_tsunami_alert_data():
    """Get tsunami alerts for map display"""
    try:
        tsunami_alerts = await disaster_api_service.get_tsunami_alerts()
        
        # Add mock data for demonstration if no real data available
        if not tsunami_alerts:
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
        
        # Convert to format expected by the map component
        formatted_alerts = [
            {
                "id": alert.id,
                "location": alert.area,
                "level": alert.alert_level.value,
                "time": alert.timestamp.isoformat(),
                "latitude": 35.6762,  # Default to Tokyo coordinates if not available
                "longitude": 139.6503  # Will be improved with actual coordinate data
            }
            for alert in tsunami_alerts
        ]
        
        return formatted_alerts
        
    except Exception as e:
        logger.error(f"Error fetching tsunami alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tsunami alerts")


@app.get("/api/weather/wind")
async def get_wind_data():
    """Get real-time wind data for major Japanese cities"""
    try:
        # OpenWeatherMap API key (free tier available)
        # You can get a free API key from https://openweathermap.org/api
        API_KEY = "demo_key"  # Replace with actual API key
        
        cities = [
            {"name": "東京", "lat": 35.6762, "lon": 139.6503},
            {"name": "大阪", "lat": 34.6937, "lon": 135.5023},
            {"name": "横浜", "lat": 35.4437, "lon": 139.6380}
        ]
        
        wind_data = []
        
        async with httpx.AsyncClient() as client:
            for city in cities:
                try:
                    # If no API key is set, return mock data
                    if API_KEY == "demo_key":
                        # Return enhanced mock data with more realistic values
                        import random
                        base_speed = random.randint(5, 25)
                        gusts = base_speed + random.randint(5, 15)
                        directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
                        direction = random.choice(directions)
                        
                        # Determine status based on wind speed
                        if base_speed < 10:
                            status = "calm"
                        elif base_speed < 20:
                            status = "normal"
                        else:
                            status = "moderate"
                        
                        wind_data.append({
                            "location": city["name"],
                            "speed": f"{base_speed} km/h",
                            "direction": direction,
                            "gusts": f"{gusts} km/h",
                            "status": status,
                            "timestamp": datetime.now().isoformat(),
                            "temperature": f"{random.randint(15, 30)}°C",
                            "humidity": f"{random.randint(40, 80)}%"
                        })
                    else:
                        # Real API call to OpenWeatherMap
                        url = f"https://api.openweathermap.org/data/2.5/weather"
                        params = {
                            "lat": city["lat"],
                            "lon": city["lon"],
                            "appid": API_KEY,
                            "units": "metric",
                            "lang": "ja"
                        }
                        
                        response = await client.get(url, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            wind = data.get("wind", {})
                            main = data.get("main", {})
                            
                            # Convert wind speed from m/s to km/h
                            speed_ms = wind.get("speed", 0)
                            speed_kmh = round(speed_ms * 3.6, 1)
                            
                            # Convert wind direction from degrees to Japanese direction
                            def deg_to_direction(deg):
                                directions = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
                                            "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
                                return directions[int((deg + 11.25) / 22.5) % 16]
                            
                            direction = deg_to_direction(wind.get("deg", 0))
                            
                            # Estimate gusts (usually 1.3-1.5x wind speed if not provided)
                            gusts_ms = wind.get("gust", speed_ms * 1.4)
                            gusts_kmh = round(gusts_ms * 3.6, 1)
                            
                            # Determine status based on wind speed
                            if speed_kmh < 10:
                                status = "calm"
                            elif speed_kmh < 20:
                                status = "normal"
                            else:
                                status = "moderate"
                            
                            wind_data.append({
                                "location": city["name"],
                                "speed": f"{speed_kmh} km/h",
                                "direction": direction,
                                "gusts": f"{gusts_kmh} km/h",
                                "status": status,
                                "timestamp": datetime.now().isoformat(),
                                "temperature": f"{round(main.get('temp', 20))}°C",
                                "humidity": f"{main.get('humidity', 50)}%"
                            })
                        else:
                            # Fallback to mock data if API fails
                            wind_data.append({
                                "location": city["name"],
                                "speed": "-- km/h",
                                "direction": "--",
                                "gusts": "-- km/h",
                                "status": "unknown",
                                "timestamp": datetime.now().isoformat(),
                                "temperature": "--°C",
                                "humidity": "--%"
                            })
                            
                except Exception as e:
                    logger.error(f"Error fetching weather data for {city['name']}: {e}")
                    # Fallback to mock data for this city
                    wind_data.append({
                        "location": city["name"],
                        "speed": "-- km/h",
                        "direction": "--",
                        "gusts": "-- km/h", 
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "temperature": "--°C",
                        "humidity": "--%"
                    })
        
        # Return JSON response with explicit UTF-8 encoding
        return JSONResponse(
            content=wind_data,
            media_type="application/json; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error fetching wind data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch wind data")


@app.get("/api/debug/messages")
async def debug_get_messages():
    """Debug endpoint for messages"""
    try:
        return [{"message": "debug works", "timestamp": datetime.now().isoformat()}]
    except Exception as e:
        return {"error": str(e)}


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": "The requested resource was not found"}
    )


# @app.exception_handler(500)
# async def internal_error_handler(request, exc):
#     logger.error(f"Internal server error: {exc}")
#     return JSONResponse(
#         status_code=500,
#         content={"error": "Internal server error", "message": "An unexpected error occurred"}
#     )


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 