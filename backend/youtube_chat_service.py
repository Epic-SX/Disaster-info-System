#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live Chat Service
Enhanced implementation using pytchat library for real-time chat analysis and auto-response
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
from typing import Dict, List, Optional, Tuple, Any
import websockets
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import pytchat
    PYTCHAT_AVAILABLE = True
    logging.info("✓ pytchat library loaded successfully")
except ImportError as e:
    PYTCHAT_AVAILABLE = False
    logging.error(f"❌ pytchat is not available: {e}")
    logging.error("Install with: pip install pytchat")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. AI responses will be disabled.")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
    logging.info("✓ Google API libraries loaded successfully")
except ImportError as e:
    GOOGLE_API_AVAILABLE = False
    logging.error(f"❌ Google API libraries not available: {e}")
    logging.error("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

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
    amount_value: Optional[float] = None
    currency: Optional[str] = None
    message_type: str = "text"
    sentiment_score: Optional[float] = None
    category: Optional[str] = None

@dataclass
class AutoResponseRule:
    """Auto response rule configuration"""
    id: int
    keywords: List[str]
    response: str
    response_type: str
    priority: int = 1
    cooldown: int = 30
    enabled: bool = True

class YouTubeChatAnalyzer:
    """Enhanced YouTube Live Chat analyzer with pytchat integration"""
    
    def __init__(self, video_id: str, config_path: str = "config.json"):
        self.video_id = video_id
        self.chat = None
        self.running = False
        self.db_path = "chat_data.db"
        
        # Google API credentials
        self.credentials_path = "../august-key-430913-i2-3e7c61487160.json"
        self.youtube_service = None
        self.live_chat_id = None
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize Google API
        self._init_google_api()
        
        # Initialize database
        self._init_database()
        
        # Auto response patterns
        self.auto_responses = self._load_auto_responses()
        
        # Keywords for disaster information (from article reference)
        self.disaster_keywords = [
            "地震", "津波", "台風", "豪雨", "火事", "災害", "避難", "緊急", "警報", "注意報",
            "earthquake", "tsunami", "typhoon", "fire", "disaster", "emergency", "alert", "warning"
        ]
        
        self.product_keywords = [
            "防災グッズ", "非常食", "懐中電灯", "ラジオ", "防災リュック", "応急手当", "備蓄",
            "disaster kit", "emergency food", "flashlight", "radio", "first aid", "emergency supplies"
        ]
        
        # Response cooldown tracking (seconds)
        self.last_response_time = {}
        self.response_cooldown = self.config.get('auto_response_cooldown', 30)
        
        # Message processing queue
        self.message_queue = asyncio.Queue()
        
        # Statistics tracking
        self.stats = {
            'total_messages': 0,
            'disaster_mentions': 0,
            'product_mentions': 0,
            'auto_responses_sent': 0,
            'start_time': datetime.now()
        }

        # OpenAI setup
        if self.config.get('openai_api_key') and OPENAI_AVAILABLE:
            openai.api_key = self.config['openai_api_key']
            self.ai_enabled = True
            logger.info("✓ OpenAI API configured for AI responses")
        else:
            self.ai_enabled = False
            logger.warning("⚠️ OpenAI API not configured - AI responses disabled")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file and environment variables"""
        default_config = {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
            'auto_response_enabled': True,
            'ai_response_enabled': True,
            'auto_response_cooldown': 30,
            'max_chat_history': 1000,
            'sentiment_threshold': 0.7,
            'ai_model': 'gpt-3.5-turbo',
            'max_tokens': 150,
            'temperature': 0.7
        }
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using defaults and environment variables.")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}. Using defaults.")
        
        return default_config

    def _init_google_api(self):
        """Initialize Google API service for YouTube operations"""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("⚠️ Google API libraries not available - YouTube API features disabled")
            return
        
        try:
            if os.path.exists(self.credentials_path):
                # Use service account credentials
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/youtube.force-ssl']
                )
                
                self.youtube_service = build('youtube', 'v3', credentials=credentials)
                logger.info("✓ YouTube API service initialized with service account credentials")
                
                # Get live chat ID if video ID is provided
                if self.video_id and self.video_id != 'development_mode':
                    self._get_live_chat_id()
                    
            else:
                logger.error(f"❌ Service account credentials file not found: {self.credentials_path}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google API: {e}")
            self.youtube_service = None

    def _get_live_chat_id(self):
        """Get the live chat ID for the current video"""
        if not self.youtube_service:
            return
        
        try:
            # Get video details to extract live chat ID
            request = self.youtube_service.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            )
            response = request.execute()
            
            if response['items']:
                live_details = response['items'][0].get('liveStreamingDetails', {})
                self.live_chat_id = live_details.get('activeLiveChatId')
                
                if self.live_chat_id:
                    logger.info(f"✓ Live chat ID obtained: {self.live_chat_id}")
                else:
                    logger.warning("⚠️ No active live chat found for this video")
            else:
                logger.warning(f"⚠️ Video not found: {self.video_id}")
                
        except Exception as e:
            logger.error(f"❌ Error getting live chat ID: {e}")

    def _init_database(self):
        """Initialize SQLite database for chat storage with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enhanced chat messages table
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
                amount_value REAL,
                currency TEXT,
                message_type TEXT,
                category TEXT,
                sentiment REAL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Auto responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                response TEXT,
                timestamp DATETIME,
                category TEXT,
                response_type TEXT,
                sent_successfully BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (message_id) REFERENCES chat_messages (id)
            )
        ''')
        
        # Auto response rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT,
                response TEXT,
                response_type TEXT,
                priority INTEGER DEFAULT 1,
                cooldown INTEGER DEFAULT 30,
                enabled BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                used_count INTEGER DEFAULT 0,
                last_used_at DATETIME
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                total_messages INTEGER DEFAULT 0,
                disaster_mentions INTEGER DEFAULT 0,
                product_mentions INTEGER DEFAULT 0,
                auto_responses_sent INTEGER DEFAULT 0,
                average_sentiment REAL DEFAULT 0.0,
                unique_users INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✓ Database initialized successfully")

    def _load_auto_responses(self) -> List[AutoResponseRule]:
        """Load auto response rules from database and defaults"""
        rules = []
        
        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM response_rules WHERE enabled = TRUE ORDER BY priority')
        db_rules = cursor.fetchall()
        
        for rule in db_rules:
            rules.append(AutoResponseRule(
                id=rule[0],
                keywords=rule[1].split(','),
                response=rule[2],
                response_type=rule[3],
                priority=rule[4],
                cooldown=rule[5],
                enabled=bool(rule[6])
            ))
        
        conn.close()
        
        # Add default rules if database is empty
        if not rules:
            default_rules = [
                AutoResponseRule(
                    id=1,
                    keywords=["こんにちは", "hello", "hi"],
                    response="こんにちは！災害情報配信をご視聴いただき、ありがとうございます！🙋‍♀️",
                    response_type="greeting",
                    priority=1
                ),
                AutoResponseRule(
                    id=2,
                    keywords=["地震", "earthquake"],
                    response="🚨 地震情報を確認中です。最新情報は画面の地震データをご確認ください。公式発表をお待ちください。",
                    response_type="disaster",
                    priority=2
                ),
                AutoResponseRule(
                    id=3,
                    keywords=["津波", "tsunami"],
                    response="🌊 津波に関する情報は気象庁の公式発表をご確認ください。海岸近くの方は直ちに高台へ避難してください。",
                    response_type="disaster",
                    priority=2
                ),
                AutoResponseRule(
                    id=4,
                    keywords=["防災グッズ", "disaster kit", "emergency supplies"],
                    response="🎒 防災グッズの情報はこちらをご参考ください。非常食、懐中電灯、ラジオ、応急手当用品をご準備ください。",
                    response_type="product",
                    priority=3
                )
            ]
            
            # Save default rules to database
            self._save_default_rules(default_rules)
            rules = default_rules
        
        logger.info(f"✓ Loaded {len(rules)} auto response rules")
        return rules

    def _save_default_rules(self, rules: List[AutoResponseRule]):
        """Save default auto response rules to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for rule in rules:
            cursor.execute('''
                INSERT OR REPLACE INTO response_rules 
                (keywords, response, response_type, priority, cooldown, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ','.join(rule.keywords),
                rule.response,
                rule.response_type,
                rule.priority,
                rule.cooldown,
                rule.enabled
            ))
        
        conn.commit()
        conn.close()

    async def start_monitoring(self):
        """Start monitoring YouTube Live Chat using pytchat"""
        if not PYTCHAT_AVAILABLE:
            logger.error("❌ pytchat library is not available. Cannot start monitoring.")
            return
        
        if self.video_id == 'development_mode':
            logger.info("🔧 Running in development mode - no real chat monitoring")
            await self._run_development_mode()
            return
        
        try:
            # Initialize pytchat
            logger.info(f"🚀 Starting chat monitoring for video: {self.video_id}")
            self.chat = pytchat.create(video_id=self.video_id)
            self.running = True
            
            # Start message processing task
            processing_task = asyncio.create_task(self._process_message_queue())
            
            logger.info("✓ Chat monitoring started successfully")
            
            # Main chat monitoring loop
            while self.running and self.chat.is_alive():
                try:
                    # Get chat messages using pytchat
                    for chat_data in self.chat.get().sync():
                        message = self._parse_pytchat_message(chat_data)
                        if message:
                            # Add to processing queue
                            await self.message_queue.put(message)
                            self.stats['total_messages'] += 1
                            
                except Exception as e:
                    logger.error(f"❌ Error getting chat messages: {e}")
                    await asyncio.sleep(2)  # Wait before retrying
                    
                # Brief delay to prevent excessive API calls
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Error starting chat monitoring: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            if self.chat:
                self.chat.terminate()
                logger.info("🛑 Chat monitoring terminated")
            
            # Cancel processing task
            if 'processing_task' in locals():
                processing_task.cancel()

    def _parse_pytchat_message(self, chat_data) -> Optional[ChatMessage]:
        """Parse pytchat message data into ChatMessage object"""
        try:
            # Parse timestamp - pytchat provides datetime as string
            timestamp_str = chat_data.datetime
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            timestamp = datetime.fromisoformat(timestamp_str)
            
            # Extract amount and currency for Super Chat
            amount_value = None
            currency = None
            message_type = "text"
            
            if hasattr(chat_data, 'amountValue') and chat_data.amountValue:
                amount_value = float(chat_data.amountValue)
                currency = getattr(chat_data, 'currency', None)
                message_type = "super_chat"
            
            message = ChatMessage(
                id=chat_data.id,
                author=chat_data.author.name,
                message=chat_data.message,
                timestamp=timestamp,
                is_owner=getattr(chat_data.author, 'isOwner', False),
                is_moderator=getattr(chat_data.author, 'isModerator', False),
                is_member=getattr(chat_data.author, 'isChatMember', False),
                amount_value=amount_value,
                currency=currency,
                message_type=message_type
            )
            
            logger.debug(f"📨 Parsed message from {message.author}: {message.message[:50]}...")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error parsing chat message: {e}")
            return None

    async def _run_development_mode(self):
        """Run in development mode with simulated messages"""
        logger.info("🔧 Running in development mode...")
        
        # Generate some mock messages for testing
        mock_messages = [
            ("TestUser1", "こんにちは！"),
            ("DisasterWatcher", "地震の情報はありますか？"),
            ("PreparedCitizen", "防災グッズはどこで買えますか？"),
            ("ViewerA", "津波警報は出ていますか？"),
            ("ViewerB", "ありがとうございます！")
        ]
        
        while self.running:
            for author, message_text in mock_messages:
                if not self.running:
                    break
                
                mock_message = ChatMessage(
                    id=f"dev_{int(time.time())}_{author}",
                    author=author,
                    message=message_text,
                    timestamp=datetime.now(),
                    is_owner=False,
                    is_moderator=False,
                    is_member=False
                )
                
                await self.message_queue.put(mock_message)
                self.stats['total_messages'] += 1
                
                # Wait 5-10 seconds between messages
                await asyncio.sleep(5 + (time.time() % 5))
        
        logger.info("🛑 Development mode monitoring stopped")

    async def _process_message_queue(self):
        """Process messages from the queue"""
        logger.info("🔄 Message processing task started")
        
        while self.running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._process_message(message)
                
            except asyncio.TimeoutError:
                continue  # No message in queue, continue
            except Exception as e:
                logger.error(f"❌ Error processing message queue: {e}")

    async def _process_message(self, message: ChatMessage):
        """Process a single chat message with enhanced analysis"""
        try:
            # Save to database
            await self._save_message(message)
            
            # Analyze sentiment and category
            category = self._categorize_message(message.message)
            message.category = category
            
            if self.ai_enabled:
                sentiment = await self._analyze_sentiment(message.message)
                message.sentiment_score = sentiment
            
            # Update statistics
            if category == "disaster":
                self.stats['disaster_mentions'] += 1
            elif category == "product":
                self.stats['product_mentions'] += 1
            
            # Update database with analysis
            await self._update_message_analysis(message.id, category, message.sentiment_score)
            
            # Generate auto response if needed
            if self.config.get('auto_response_enabled', True):
                response = await self._generate_auto_response(message)
                if response:
                    await self._send_auto_response(message, response)
            
            # Log for monitoring
            logger.info(f"✅ Processed message from {message.author}: {message.message[:50]}... (category: {category})")
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")

    async def _save_message(self, message: ChatMessage):
        """Save chat message to database with enhanced data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO chat_messages 
            (id, video_id, author, message, timestamp, is_owner, is_moderator, is_member,
             amount_value, currency, message_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.id, self.video_id, message.author, message.message,
            message.timestamp, message.is_owner, message.is_moderator, message.is_member,
            message.amount_value, message.currency, message.message_type
        ))
        
        conn.commit()
        conn.close()

    def _categorize_message(self, message: str) -> str:
        """Categorize message based on keywords with enhanced logic"""
        message_lower = message.lower()
        
        # Check for disaster-related keywords
        disaster_score = 0
        for keyword in self.disaster_keywords:
            if keyword.lower() in message_lower:
                disaster_score += 1
        
        # Check for product-related keywords
        product_score = 0
        for keyword in self.product_keywords:
            if keyword.lower() in message_lower:
                product_score += 1
        
        # Determine category based on scores
        if disaster_score > 0:
            return "disaster"
        elif product_score > 0:
            return "product"
        
        # Check for questions
        question_indicators = ["?", "？", "どう", "なに", "なん", "いつ", "どこ", "だれ", 
                             "how", "what", "when", "where", "who", "why"]
        if any(q in message_lower for q in question_indicators):
            return "question"
        
        # Check for greetings
        greeting_indicators = ["こんにちは", "こんばんは", "おはよう", "hello", "hi", "hey"]
        if any(g in message_lower for g in greeting_indicators):
            return "greeting"
        
        return "general"

    async def _analyze_sentiment(self, message: str) -> float:
        """Analyze sentiment of message using OpenAI with enhanced prompt"""
        if not self.ai_enabled:
            return 0.0
        
        try:
            # Create chat completion for sentiment analysis
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('ai_model', 'gpt-3.5-turbo'),
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze the sentiment of the following Japanese/English text and return a score between -1 (very negative) and 1 (very positive). 
                        Consider:
                        - Emergency/disaster contexts may seem negative but could be neutral information seeking
                        - Gratitude and helpful responses are positive
                        - Complaints or anger are negative
                        - Questions are typically neutral (0.0)
                        Return only a decimal number between -1 and 1."""
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
            sentiment = float(sentiment_str)
            
            # Clamp to valid range
            sentiment = max(-1.0, min(1.0, sentiment))
            
            logger.debug(f"Sentiment analysis: '{message[:30]}...' -> {sentiment}")
            return sentiment
            
        except Exception as e:
            logger.error(f"❌ Error analyzing sentiment: {e}")
            return 0.0

    async def _update_message_analysis(self, message_id: str, category: str, sentiment: Optional[float]):
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
        """Generate auto response based on message content with cooldown and priority"""
        # Check global cooldown
        current_time = time.time()
        if (message.author in self.last_response_time and 
            current_time - self.last_response_time[message.author] < self.response_cooldown):
            return None
        
        message_lower = message.message.lower()
        
        # Find matching auto response with highest priority
        best_response = None
        highest_priority = 999  # Lower numbers = higher priority
        
        for auto_response in self.auto_responses:
            if not auto_response.enabled:
                continue
                
            # Check if any keyword matches
            for keyword in auto_response.keywords:
                if keyword.lower() in message_lower:
                    if auto_response.priority < highest_priority:
                        best_response = auto_response
                        highest_priority = auto_response.priority
                        break
        
        # If we found a matching rule, use it
        if best_response:
            self.last_response_time[message.author] = current_time
            
            # Update usage statistics
            await self._update_rule_usage(best_response.id)
            
            return best_response.response
        
        # Generate AI response for complex questions if enabled
        if (self.ai_enabled and message.category == "question" and 
            self.config.get('ai_response_enabled', True)):
            return await self._generate_ai_response(message.message)
        
        return None

    async def _update_rule_usage(self, rule_id: int):
        """Update auto response rule usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE response_rules 
            SET used_count = used_count + 1, last_used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (rule_id,))
        
        conn.commit()
        conn.close()

    async def _generate_ai_response(self, message: str) -> Optional[str]:
        """Generate AI response using OpenAI with enhanced disaster-focused prompt"""
        if not self.ai_enabled:
            return None
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('ai_model', 'gpt-3.5-turbo'),
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful disaster information assistant for a Japanese YouTube live stream about disaster preparedness and emergency information.

GUIDELINES:
- Respond briefly and helpfully to questions about disasters, emergency preparedness, and safety
- Keep responses under 200 characters to fit chat format
- Use Japanese if the question is in Japanese, English if in English
- Always encourage viewers to check official sources (気象庁, 消防庁, etc.) for the latest information
- For emergency situations, prioritize safety and evacuation advice
- Be calm, informative, and supportive

TOPICS TO HELP WITH:
- Earthquake preparedness and response
- Tsunami warnings and evacuation
- Typhoon and weather emergencies  
- Disaster supply kits and emergency preparations
- Evacuation procedures and safety tips

If you can't provide specific information, direct them to official sources."""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=self.config.get('max_tokens', 100),
                temperature=self.config.get('temperature', 0.7)
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"🤖 Generated AI response: {ai_response}")
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Error generating AI response: {e}")
            return None

    async def _send_auto_response(self, original_message: ChatMessage, response: str):
        """Send auto response to YouTube Live Chat"""
        try:
            # Save the auto response to database first
            await self._save_auto_response(original_message, response)
            
            # If we have YouTube API access and live chat ID, send real response
            if self.youtube_service and self.live_chat_id:
                success = await self._send_youtube_message(response)
                if success:
                    logger.info(f"✅ Auto response sent to {original_message.author}: {response}")
                    self.stats['auto_responses_sent'] += 1
                else:
                    logger.warning(f"⚠️ Failed to send auto response via YouTube API")
            else:
                # Simulate sending response (development/testing)
                logger.info(f"🔧 [SIMULATED] Auto response to {original_message.author}: {response}")
                self.stats['auto_responses_sent'] += 1
            
            # Send via WebSocket to frontend for real-time display
            await self._broadcast_websocket_message({
                "type": "auto_response",
                "original_message": {
                    "id": original_message.id,
                    "author": original_message.author,
                    "message": original_message.message,
                    "timestamp": original_message.timestamp.isoformat()
                },
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "category": original_message.category
            })
            
        except Exception as e:
            logger.error(f"❌ Error sending auto response: {e}")

    async def _send_youtube_message(self, message_text: str) -> bool:
        """Send message to YouTube Live Chat via API"""
        if not self.youtube_service or not self.live_chat_id:
            return False
        
        try:
            request = self.youtube_service.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": self.live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": message_text
                        }
                    }
                }
            )
            
            response = request.execute()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending YouTube message: {e}")
            return False

    async def _save_auto_response(self, original_message: ChatMessage, response: str):
        """Save auto response to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auto_responses 
            (message_id, response, timestamp, category, response_type, sent_successfully)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            original_message.id,
            response,
            datetime.now(),
            original_message.category or "auto_response",
            "auto",
            True  # Assume success for now
        ))
        
        conn.commit()
        conn.close()

    async def _broadcast_websocket_message(self, message: Dict):
        """Broadcast message to connected WebSocket clients"""
        # This would integrate with your main WebSocket broadcasting system
        # For now, just log the message
        logger.debug(f"📡 Broadcasting WebSocket message: {message}")

    def get_chat_statistics(self, hours: int = 24) -> Dict:
        """Get comprehensive chat statistics for the last N hours"""
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
        
        # Unique users
        cursor.execute('''
            SELECT COUNT(DISTINCT author) FROM chat_messages 
            WHERE video_id = ? AND timestamp > ?
        ''', (self.video_id, since))
        unique_users = cursor.fetchone()[0]
        
        # Super Chat information
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount_value), 0) FROM chat_messages 
            WHERE video_id = ? AND timestamp > ? AND message_type = 'super_chat'
        ''', (self.video_id, since))
        super_chat_count, super_chat_total = cursor.fetchone()
        
        # Top keywords
        cursor.execute('''
            SELECT message FROM chat_messages 
            WHERE video_id = ? AND timestamp > ?
        ''', (self.video_id, since))
        
        messages = cursor.fetchall()
        word_count = {}
        
        for (message,) in messages:
            # Extract Japanese and English words
            words = re.findall(r'[\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]+', message.lower())
            for word in words:
                if len(word) > 1:  # Ignore single characters
                    word_count[word] = word_count.get(word, 0) + 1
        
        top_keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Auto response statistics
        cursor.execute('''
            SELECT COUNT(*) FROM auto_responses 
            WHERE timestamp > ?
        ''', (since,))
        auto_responses_sent = cursor.fetchone()[0]
        
        conn.close()
        
        # Current session statistics
        session_stats = {
            "session_start": self.stats['start_time'].isoformat(),
            "session_messages": self.stats['total_messages'],
            "session_disaster_mentions": self.stats['disaster_mentions'],
            "session_product_mentions": self.stats['product_mentions'],
            "session_auto_responses": self.stats['auto_responses_sent']
        }
        
        return {
            "total_messages": total_messages,
            "categories": categories,
            "average_sentiment": round(avg_sentiment, 3),
            "unique_users": unique_users,
            "super_chat_count": super_chat_count,
            "super_chat_total": super_chat_total,
            "top_keywords": top_keywords,
            "auto_responses_sent": auto_responses_sent,
            "period_hours": hours,
            "session_statistics": session_stats,
            "is_live": self.running and (self.chat.is_alive() if self.chat else False)
        }

    def get_recent_messages(self, limit: int = 50) -> List[Dict]:
        """Get recent chat messages from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, author, message, timestamp, category, sentiment, message_type, amount_value, currency
            FROM chat_messages 
            WHERE video_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (self.video_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "id": row[0],
                "author": row[1],
                "message": row[2],
                "timestamp": row[3],
                "category": row[4],
                "sentiment_score": row[5],
                "message_type": row[6],
                "amount_value": row[7],
                "currency": row[8],
                "platform": "youtube"
            })
        
        conn.close()
        return messages

    def stop_monitoring(self):
        """Stop chat monitoring gracefully"""
        logger.info("🛑 Stopping chat monitoring...")
        self.running = False
        
        if self.chat:
            try:
                self.chat.terminate()
                logger.info("✅ pytchat terminated successfully")
            except Exception as e:
                logger.error(f"❌ Error terminating pytchat: {e}")
        
        logger.info("✅ Chat monitoring stopped")

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