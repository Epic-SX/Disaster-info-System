#!/usr/bin/env python3
"""
Simplified startup script for the Disaster Information System backend.
This script imports only essential modules to avoid dependency issues.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import json

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""
    debug: bool = True
    port: int = 8000
    host: str = "0.0.0.0"  # Changed from localhost to bind to all interfaces
    log_level: str = "INFO"
    
    # Database settings
    database_url: str = "sqlite:///disaster_chat.db"
    
    # Chat settings
    max_chat_history: int = 1000
    sentiment_threshold: float = 0.7
    auto_response_cooldown: int = 30
    
    # API Keys
    openai_api_key: str = ""
    youtube_api_key: str = ""
    serpapi_api_key: str = ""
    
    # AI settings
    ai_model: str = "gpt-3.5-turbo"
    max_tokens: int = 150
    temperature: float = 0.7
    
    # Alert thresholds
    earthquake_magnitude_threshold: float = 5.0
    tsunami_height_threshold: float = 1.0
    wind_speed_threshold: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

# Update logging level based on settings
logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

logger.info("=== Disaster Information System Backend Starting ===")
logger.info(f"DEBUG: {settings.debug}")
logger.info(f"PORT: {settings.port}")
logger.info(f"HOST: {settings.host}")
logger.info(f"LOG_LEVEL: {settings.log_level}")
logger.info(f"OPENAI_API_KEY: {'SET' if settings.openai_api_key else 'NOT SET'}")
logger.info(f"SERPAPI_API_KEY: {'SET' if settings.serpapi_api_key else 'NOT SET'}")
logger.info("================================================")

# Global variables
connected_websockets: List[WebSocket] = []
chat_messages: List[dict] = []


# Pydantic models
class ChatMessage(BaseModel):
    id: str
    message_id: str
    author: str
    message: str
    timestamp: str
    sentiment_score: float
    category: str
    platform: str


class ChatAnalytics(BaseModel):
    total_messages: int
    disaster_mentions: int
    product_mentions: int
    sentiment_score: float
    top_keywords: List[str]
    active_users: int


class AutoResponse(BaseModel):
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
    logger.info("Starting Disaster Information System backend...")
    yield
    logger.info("Shutting down Disaster Information System backend...")


# Create FastAPI app
app = FastAPI(
    title="Disaster Information System API",
    description="Backend API for real-time disaster information and monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://49.212.176.130:3000",  # Remote server frontend
        "http://49.212.176.130:3001",  # Remote server frontend alternative port
        "http://49.212.176.130",  # Remote server root
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
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
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
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


# API Routes
@app.get("/")
async def root():
    """API information and available endpoints"""
    return {
        "message": "Disaster Information System API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "websocket_connections": len(connected_websockets)
    }


@app.get("/api/chat/messages")
async def get_chat_messages(limit: int = 50):
    """Get recent chat messages"""
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
        }
    ]
    return mock_messages[:limit]


@app.get("/api/chat/analytics", response_model=ChatAnalytics)
async def get_chat_analytics():
    """Get chat analytics"""
    return ChatAnalytics(
        total_messages=142,
        disaster_mentions=23,
        product_mentions=18,
        sentiment_score=0.6,
        top_keywords=["地震", "防災", "津波", "備え", "安全"],
        active_users=47
    )


@app.post("/api/chat/response")
async def send_chat_response(request: dict):
    """Send a response to chat"""
    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    return {"status": "success", "message": "Response sent (development mode)"}


@app.get("/api/chat/responses", response_model=List[AutoResponse])
async def get_auto_responses():
    """Get configured auto-responses"""
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


@app.get("/api/earthquake/recent")
async def get_recent_earthquake_data():
    """Get recent earthquake data for map display"""
    import random
    mock_earthquakes = [
        {
            "id": "mock_eq_1",
            "time": (datetime.now()).isoformat(),
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
            "time": datetime.now().isoformat(),
            "location": "千葉県東方沖",
            "magnitude": 5.2,
            "depth": 50,
            "latitude": 35.7601,
            "longitude": 140.4097,
            "intensity": "5-",
            "tsunami": False
        }
    ]
    return mock_earthquakes


@app.get("/api/tsunami/alerts")
async def get_tsunami_alert_data():
    """Get tsunami alerts for map display"""
    mock_tsunamis = [
        {
            "id": "mock_tsunami_1",
            "location": "宮城県沿岸",
            "level": "warning",
            "time": datetime.now().isoformat(),
            "latitude": 38.2682,
            "longitude": 140.8694
        }
    ]
    return mock_tsunamis


@app.get("/api/weather/wind")
async def get_wind_data():
    """Get wind data for multiple Japanese cities"""
    import random
    
    cities = [
        {"name": "東京"},
        {"name": "大阪"},
        {"name": "横浜"},
        {"name": "名古屋"},
        {"name": "福岡"}
    ]
    
    wind_data = []
    
    for city in cities:
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
    
    return JSONResponse(content=wind_data, media_type="application/json; charset=utf-8")


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "start:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 