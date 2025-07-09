#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live Chat Service
Based on pytchat library for real-time chat analysis and auto-response
Reference: https://brian0111.com/youtube-live-chat-pytchat-python/
"""

import os
import json
import time
import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import websockets
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import pytchat
    PYTCHAT_AVAILABLE = True
except ImportError:
    PYTCHAT_AVAILABLE = False
    print("pytchat is not installed. Install with: pip install pytchat")

import openai
import requests
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """YouTube Live Chat message data class"""
    id: str
    author: str
    message: str
    timestamp: datetime
    is_owner: bool = False
    is_moderator: bool = False
    is_member: bool = False

@dataclass
class AutoResponse:
    """Auto response configuration"""
    keywords: List[str]
    response: str
    category: str
    priority: int = 1

class YouTubeChatAnalyzer:
    """YouTube Live Chat analyzer and auto-responder"""
    
    def __init__(self, video_id: str, config_path: str = "config.json"):
        self.video_id = video_id
        self.chat = None
        self.running = False
        self.db_path = "chat_data.db"
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize database
        self._init_database()
        
        # Auto response patterns
        self.auto_responses = self._load_auto_responses()
        
        # Keywords for disaster information
        self.disaster_keywords = [
            "地震", "津波", "台風", "豪雨", "火事", "災害", "避難", "緊急",
            "earthquake", "tsunami", "typhoon", "fire", "disaster", "emergency"
        ]
        
        self.product_keywords = [
            "防災グッズ", "非常食", "懐中電灯", "ラジオ", "防災リュック",
            "disaster kit", "emergency food", "flashlight", "radio"
        ]
        
        # Response cooldown (seconds)
        self.last_response_time = {}
        self.response_cooldown = 30
        
        # OpenAI setup
        if self.config.get('openai_api_key'):
            openai.api_key = self.config['openai_api_key']

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using defaults.")
            return {
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
                'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
                'auto_response_enabled': True,
                'ai_response_enabled': True
            }

    def _init_database(self):
        """Initialize SQLite database for chat storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                video_id TEXT,
                author TEXT,
                message TEXT,
                timestamp DATETIME,
                is_owner BOOLEAN,
                is_moderator BOOLEAN,
                is_member BOOLEAN,
                category TEXT,
                sentiment REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                response TEXT,
                timestamp DATETIME,
                category TEXT,
                FOREIGN KEY (message_id) REFERENCES chat_messages (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _load_auto_responses(self) -> List[AutoResponse]:
        """Load predefined auto response patterns"""
        return [
            AutoResponse(
                keywords=["地震", "earthquake", "揺れ"],
                response="🚨 地震情報を確認中です。最新情報は画面左上の地震情報パネルをご覧ください。身の安全を最優先にしてください。",
                category="earthquake",
                priority=1
            ),
            AutoResponse(
                keywords=["津波", "tsunami"],
                response="🌊 津波情報については、画面の津波情報パネルで最新状況をお伝えしています。海岸付近の方は高台への避難をお願いします。",
                category="tsunami",
                priority=1
            ),
            AutoResponse(
                keywords=["防災グッズ", "disaster kit", "非常食", "備蓄"],
                response="🎒 おすすめの防災グッズ情報はこちら: https://example.com/disaster-kit \n水・食料・懐中電灯・ラジオ・医薬品の準備をお忘れなく！",
                category="products",
                priority=2
            ),
            AutoResponse(
                keywords=["避難場所", "避難所", "evacuation"],
                response="📍 お住まいの地域の避難場所は、各自治体のハザードマップでご確認ください。事前の確認が重要です。",
                category="evacuation",
                priority=1
            ),
            AutoResponse(
                keywords=["ライブ配信", "配信", "stream", "live"],
                response="📺 24時間災害情報をライブ配信中です！チャンネル登録・通知設定をして最新情報をお受け取りください。",
                category="promotion",
                priority=3
            )
        ]

    async def start_monitoring(self):
        """Start monitoring YouTube Live Chat"""
        if not PYTCHAT_AVAILABLE:
            logger.error("pytchat library is not available")
            return
        
        try:
            self.chat = pytchat.create(video_id=self.video_id)
            self.running = True
            logger.info(f"Started monitoring chat for video: {self.video_id}")
            
            while self.running and self.chat.is_alive():
                try:
                    # Get chat messages
                    for c in self.chat.get().sync():
                        message = ChatMessage(
                            id=c.id,
                            author=c.author.name,
                            message=c.message,
                            timestamp=datetime.fromisoformat(c.datetime.replace('Z', '+00:00')),
                            is_owner=c.author.isOwner,
                            is_moderator=c.author.isModerator,
                            is_member=c.author.isChatMember
                        )
                        
                        # Process the message
                        await self._process_message(message)
                        
                except Exception as e:
                    logger.error(f"Error processing chat messages: {e}")
                    
                # Short delay to prevent excessive API calls
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting chat monitoring: {e}")
        finally:
            if self.chat:
                self.chat.terminate()

    async def _process_message(self, message: ChatMessage):
        """Process a single chat message"""
        try:
            # Save to database
            await self._save_message(message)
            
            # Analyze sentiment and category
            category = self._categorize_message(message.message)
            sentiment = await self._analyze_sentiment(message.message)
            
            # Update database with analysis
            await self._update_message_analysis(message.id, category, sentiment)
            
            # Generate auto response if needed
            if self.config.get('auto_response_enabled', True):
                response = await self._generate_auto_response(message)
                if response:
                    await self._send_auto_response(message, response)
            
            # Log for monitoring
            logger.info(f"Processed message from {message.author}: {message.message[:50]}...")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _save_message(self, message: ChatMessage):
        """Save chat message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO chat_messages 
            (id, video_id, author, message, timestamp, is_owner, is_moderator, is_member)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.id, self.video_id, message.author, message.message,
            message.timestamp, message.is_owner, message.is_moderator, message.is_member
        ))
        
        conn.commit()
        conn.close()

    def _categorize_message(self, message: str) -> str:
        """Categorize message based on keywords"""
        message_lower = message.lower()
        
        # Check for disaster-related keywords
        for keyword in self.disaster_keywords:
            if keyword.lower() in message_lower:
                return "disaster"
        
        # Check for product-related keywords
        for keyword in self.product_keywords:
            if keyword.lower() in message_lower:
                return "product"
        
        # Check for questions
        if any(q in message_lower for q in ["?", "？", "どう", "なに", "いつ", "どこ", "how", "what", "when", "where"]):
            return "question"
        
        return "general"

    async def _analyze_sentiment(self, message: str) -> float:
        """Analyze sentiment of message using OpenAI"""
        if not self.config.get('ai_response_enabled'):
            return 0.0
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the following Japanese/English text and return a score between -1 (very negative) and 1 (very positive). Return only the number."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=10,
                temperature=0
            )
            
            sentiment_str = response.choices[0].message.content.strip()
            return float(sentiment_str)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 0.0

    async def _update_message_analysis(self, message_id: str, category: str, sentiment: float):
        """Update message with analysis results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE chat_messages 
            SET category = ?, sentiment = ?
            WHERE id = ?
        ''', (category, sentiment, message_id))
        
        conn.commit()
        conn.close()

    async def _generate_auto_response(self, message: ChatMessage) -> Optional[str]:
        """Generate auto response based on message content"""
        # Check cooldown
        current_time = time.time()
        if (message.author in self.last_response_time and 
            current_time - self.last_response_time[message.author] < self.response_cooldown):
            return None
        
        message_lower = message.message.lower()
        
        # Find matching auto response
        best_response = None
        highest_priority = 0
        
        for auto_response in self.auto_responses:
            for keyword in auto_response.keywords:
                if keyword.lower() in message_lower:
                    if auto_response.priority < highest_priority or highest_priority == 0:
                        best_response = auto_response
                        highest_priority = auto_response.priority
                        break
        
        if best_response:
            self.last_response_time[message.author] = current_time
            return best_response.response
        
        # Generate AI response for complex questions
        if (self.config.get('ai_response_enabled') and 
            message.message.count('?') > 0 or message.message.count('？') > 0):
            return await self._generate_ai_response(message.message)
        
        return None

    async def _generate_ai_response(self, message: str) -> Optional[str]:
        """Generate AI response using OpenAI"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful disaster information assistant for a YouTube live stream. 
                        Respond briefly and helpfully to questions about disasters, emergency preparedness, and safety.
                        Keep responses under 200 characters. Use Japanese if the question is in Japanese, English if in English.
                        Always encourage viewers to check official sources for the latest information."""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None

    async def _send_auto_response(self, original_message: ChatMessage, response: str):
        """Send auto response (simulated - actual implementation would use YouTube API)"""
        # Save the auto response to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auto_responses (message_id, response, timestamp, category)
            VALUES (?, ?, ?, ?)
        ''', (
            original_message.id,
            response,
            datetime.now(),
            "auto_response"
        ))
        
        conn.commit()
        conn.close()
        
        # Log the response
        logger.info(f"Auto response to {original_message.author}: {response}")
        
        # In a real implementation, you would use YouTube API to post the response
        # For now, we'll send it through WebSocket to the frontend
        await self._send_websocket_message({
            "type": "auto_response",
            "original_message": original_message.message,
            "response": response,
            "author": original_message.author,
            "timestamp": datetime.now().isoformat()
        })

    async def _send_websocket_message(self, message: Dict):
        """Send message to frontend via WebSocket"""
        # This would connect to your WebSocket server
        # Implementation depends on your WebSocket setup
        logger.info(f"WebSocket message: {message}")

    def get_chat_statistics(self, hours: int = 24) -> Dict:
        """Get chat statistics for the last N hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        # Total messages
        cursor.execute('''
            SELECT COUNT(*) FROM chat_messages 
            WHERE video_id = ? AND timestamp > ?
        ''', (self.video_id, since))
        total_messages = cursor.fetchone()[0]
        
        # Messages by category
        cursor.execute('''
            SELECT category, COUNT(*) FROM chat_messages 
            WHERE video_id = ? AND timestamp > ? AND category IS NOT NULL
            GROUP BY category
        ''', (self.video_id, since))
        categories = dict(cursor.fetchall())
        
        # Average sentiment
        cursor.execute('''
            SELECT AVG(sentiment) FROM chat_messages 
            WHERE video_id = ? AND timestamp > ? AND sentiment IS NOT NULL
        ''', (self.video_id, since))
        avg_sentiment = cursor.fetchone()[0] or 0.0
        
        # Top keywords
        cursor.execute('''
            SELECT message FROM chat_messages 
            WHERE video_id = ? AND timestamp > ?
        ''', (self.video_id, since))
        
        messages = cursor.fetchall()
        word_count = {}
        
        for (message,) in messages:
            words = re.findall(r'\w+', message.lower())
            for word in words:
                if len(word) > 2:  # Ignore short words
                    word_count[word] = word_count.get(word, 0) + 1
        
        top_keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "categories": categories,
            "average_sentiment": avg_sentiment,
            "top_keywords": top_keywords,
            "period_hours": hours
        }

    def stop_monitoring(self):
        """Stop monitoring chat"""
        self.running = False
        if self.chat:
            self.chat.terminate()
        logger.info("Stopped chat monitoring")

# WebSocket server for real-time communication with frontend
class ChatWebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()

    async def register(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        logger.info(f"Client registered. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Unregister a client"""
        self.clients.discard(websocket)
        logger.info(f"Client unregistered. Total clients: {len(self.clients)}")

    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        if self.clients:
            message_json = json.dumps(message, ensure_ascii=False)
            await asyncio.gather(
                *[client.send(message_json) for client in self.clients],
                return_exceptions=True
            )

    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages from frontend
                data = json.loads(message)
                logger.info(f"Received message: {data}")
                
                # Echo back or process as needed
                await websocket.send(json.dumps({
                    "type": "ack",
                    "original": data
                }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def start_server(self):
        """Start the WebSocket server"""
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
        return server

# Main function to run the service
async def main():
    """Main function to run the YouTube Chat Service"""
    # Configuration
    VIDEO_ID = os.getenv('YOUTUBE_LIVE_VIDEO_ID', 'your_video_id_here')
    
    if not VIDEO_ID or VIDEO_ID == 'your_video_id_here':
        logger.error("Please set YOUTUBE_LIVE_VIDEO_ID environment variable")
        return
    
    # Initialize services
    chat_analyzer = YouTubeChatAnalyzer(VIDEO_ID)
    websocket_server = ChatWebSocketServer()
    
    # Start WebSocket server
    server = await websocket_server.start_server()
    
    # Start chat monitoring
    try:
        await chat_analyzer.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        chat_analyzer.stop_monitoring()
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main()) 