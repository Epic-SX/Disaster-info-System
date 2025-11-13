#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Commentary Service for YouTube Live Streaming
Generates automated commentary for disaster monitoring stream
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from openai import AsyncOpenAI
import aiohttp

logger = logging.getLogger(__name__)


class DisasterCommentary:
    """AI-generated commentary for disaster events"""
    
    def __init__(self, event_type: str, content: str, severity: str, timestamp: datetime):
        self.event_type = event_type
        self.content = content
        self.severity = severity
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "content": self.content,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat()
        }


class AICommentaryService:
    """
    Service to generate AI-powered automated commentary for disaster monitoring stream
    Uses OpenAI GPT to create natural language commentary based on real-time data
    """
    
    def __init__(self, openai_api_key: str, backend_url: str = "http://localhost:8000"):
        """
        Initialize AI Commentary Service
        
        Args:
            openai_api_key: OpenAI API key
            backend_url: Backend API URL for fetching disaster data
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.backend_url = backend_url
        self.last_commentary_time = {}
        self.commentary_cooldown = 60  # Minimum seconds between commentaries for same event type
        self.commentary_history = []
        self.max_history = 100
        
        # Commentary templates
        self.system_prompt = """あなたは災害情報を視聴者に伝えるプロの実況アナウンサーです。
以下の役割を担当します：

1. 地震、津波、気象情報などの災害情報をわかりやすく実況する
2. 視聴者の安全を第一に考え、必要な警告や注意喚起を行う
3. 落ち着いた口調で、パニックを避けるような表現を使う
4. 専門用語は避け、一般の方にも理解できる言葉で説明する
5. 具体的な数値や位置情報を正確に伝える

実況は簡潔に、30秒程度で話せる長さで作成してください。
"""
        
        logger.info("AI Commentary Service initialized")
    
    async def fetch_current_disasters(self) -> Dict[str, Any]:
        """Fetch current disaster data from backend"""
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch earthquake data
                async with session.get(f"{self.backend_url}/api/disasters/earthquakes/comprehensive") as response:
                    earthquakes = await response.json() if response.status == 200 else []
                
                # Fetch tsunami data
                async with session.get(f"{self.backend_url}/api/disasters/tsunami") as response:
                    tsunamis = await response.json() if response.status == 200 else []
                
                # Fetch wind data
                async with session.get(f"{self.backend_url}/api/weather/wind/summary") as response:
                    wind_data = await response.json() if response.status == 200 else {}
                
                return {
                    "earthquakes": earthquakes if isinstance(earthquakes, list) else [],
                    "tsunamis": tsunamis if isinstance(tsunamis, list) else [],
                    "wind_data": wind_data if isinstance(wind_data, dict) else {}
                }
        
        except Exception as e:
            logger.error(f"Error fetching disaster data: {str(e)}")
            return {
                "earthquakes": [],
                "tsunamis": [],
                "wind_data": {}
            }
    
    async def generate_earthquake_commentary(self, earthquake: Dict[str, Any]) -> str:
        """
        Generate commentary for an earthquake event
        
        Args:
            earthquake: Earthquake data dictionary
        
        Returns:
            Generated commentary text
        """
        try:
            # Extract earthquake details
            location = earthquake.get('location', '不明な地域')
            magnitude = earthquake.get('magnitude', 0)
            depth = earthquake.get('depth', 0)
            max_intensity = earthquake.get('max_intensity', '不明')
            time = earthquake.get('time', datetime.now().isoformat())
            
            # Create prompt
            prompt = f"""以下の地震情報について、視聴者向けの実況コメントを生成してください：

発生時刻: {time}
震源地: {location}
マグニチュード: {magnitude}
深さ: {depth}km
最大震度: {max_intensity}

この地震について、視聴者に伝えるべき重要な情報と注意点を、30秒程度で話せる長さでまとめてください。
"""
            
            # Generate commentary using OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            commentary = response.choices[0].message.content.strip()
            logger.info(f"Generated earthquake commentary: {commentary[:50]}...")
            
            return commentary
        
        except Exception as e:
            logger.error(f"Error generating earthquake commentary: {str(e)}")
            return f"{location}でマグニチュード{magnitude}の地震が発生しました。震源の深さは{depth}キロメートル、最大震度は{max_intensity}です。"
    
    async def generate_tsunami_commentary(self, tsunami: Dict[str, Any]) -> str:
        """
        Generate commentary for a tsunami alert
        
        Args:
            tsunami: Tsunami data dictionary
        
        Returns:
            Generated commentary text
        """
        try:
            location = tsunami.get('location', '不明な地域')
            warning_type = tsunami.get('type', '津波注意報')
            expected_height = tsunami.get('expected_height', '不明')
            
            prompt = f"""以下の津波情報について、視聴者向けの緊急実況コメントを生成してください：

警報種別: {warning_type}
対象地域: {location}
予想される津波の高さ: {expected_height}

津波の危険性と避難の必要性を強調し、視聴者の命を守るための実況をしてください。
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            commentary = response.choices[0].message.content.strip()
            logger.info(f"Generated tsunami commentary: {commentary[:50]}...")
            
            return commentary
        
        except Exception as e:
            logger.error(f"Error generating tsunami commentary: {str(e)}")
            return f"{location}に{warning_type}が発表されています。予想される津波の高さは{expected_height}です。海岸付近の方は直ちに高台へ避難してください。"
    
    async def generate_wind_commentary(self, wind_data: Dict[str, Any]) -> str:
        """
        Generate commentary for wind conditions
        
        Args:
            wind_data: Wind data dictionary
        
        Returns:
            Generated commentary text
        """
        try:
            if wind_data.get('status') != 'ok':
                return ""
            
            max_speed = wind_data.get('max_wind_speed', 0)
            max_location = wind_data.get('max_wind_location', '不明')
            alert_level = wind_data.get('alert_level', '通常')
            avg_speed = wind_data.get('average_wind_speed', 0)
            
            # Only generate commentary for strong winds
            if max_speed < 10:
                return ""
            
            prompt = f"""以下の風況情報について、視聴者向けの実況コメントを生成してください：

警戒レベル: {alert_level}
最大風速: {max_speed}m/s
最大風速観測地点: {max_location}
全国平均風速: {avg_speed}m/s

現在の風の状況と、視聴者が注意すべき点を簡潔に伝えてください。
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            commentary = response.choices[0].message.content.strip()
            logger.info(f"Generated wind commentary: {commentary[:50]}...")
            
            return commentary
        
        except Exception as e:
            logger.error(f"Error generating wind commentary: {str(e)}")
            return ""
    
    async def generate_periodic_status_update(self) -> str:
        """
        Generate a periodic status update commentary
        
        Returns:
            Generated status update text
        """
        try:
            current_time = datetime.now().strftime("%H時%M分")
            
            # Fetch current disaster data
            disaster_data = await self.fetch_current_disasters()
            
            earthquakes = disaster_data.get('earthquakes', [])
            tsunamis = disaster_data.get('tsunamis', [])
            wind_data = disaster_data.get('wind_data', {})
            
            prompt = f"""現在時刻{current_time}の災害監視状況について、視聴者向けの定期状況報告を生成してください：

地震情報: {len(earthquakes)}件
津波情報: {len(tsunamis)}件
風況警戒レベル: {wind_data.get('alert_level', '通常')}

全体の状況を簡潔にまとめ、視聴者に安心感を与えるまたは必要な注意喚起を行ってください。
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            commentary = response.choices[0].message.content.strip()
            logger.info(f"Generated status update: {commentary[:50]}...")
            
            return commentary
        
        except Exception as e:
            logger.error(f"Error generating status update: {str(e)}")
            current_time = datetime.now().strftime("%H時%M分")
            return f"{current_time}現在、災害監視を継続しています。"
    
    def should_generate_commentary(self, event_type: str) -> bool:
        """
        Check if enough time has passed to generate commentary for this event type
        
        Args:
            event_type: Type of event (earthquake, tsunami, wind, etc.)
        
        Returns:
            True if commentary should be generated
        """
        current_time = datetime.now()
        last_time = self.last_commentary_time.get(event_type)
        
        if last_time is None:
            return True
        
        elapsed = (current_time - last_time).total_seconds()
        return elapsed >= self.commentary_cooldown
    
    def add_to_history(self, commentary: DisasterCommentary):
        """Add commentary to history"""
        self.commentary_history.append(commentary)
        if len(self.commentary_history) > self.max_history:
            self.commentary_history.pop(0)
    
    async def generate_commentary_for_current_events(self) -> List[DisasterCommentary]:
        """
        Generate commentary for all current events
        
        Returns:
            List of generated commentaries
        """
        commentaries = []
        
        try:
            # Fetch current disaster data
            disaster_data = await self.fetch_current_disasters()
            
            # Generate earthquake commentaries
            earthquakes = disaster_data.get('earthquakes', [])
            if earthquakes and self.should_generate_commentary('earthquake'):
                # Get the most recent earthquake
                latest_eq = earthquakes[0] if isinstance(earthquakes, list) else earthquakes
                commentary_text = await self.generate_earthquake_commentary(latest_eq)
                
                commentary = DisasterCommentary(
                    event_type='earthquake',
                    content=commentary_text,
                    severity=self._determine_earthquake_severity(latest_eq),
                    timestamp=datetime.now()
                )
                commentaries.append(commentary)
                self.last_commentary_time['earthquake'] = datetime.now()
                self.add_to_history(commentary)
            
            # Generate tsunami commentaries
            tsunamis = disaster_data.get('tsunamis', [])
            if tsunamis and self.should_generate_commentary('tsunami'):
                latest_tsunami = tsunamis[0] if isinstance(tsunamis, list) else tsunamis
                commentary_text = await self.generate_tsunami_commentary(latest_tsunami)
                
                commentary = DisasterCommentary(
                    event_type='tsunami',
                    content=commentary_text,
                    severity='high',
                    timestamp=datetime.now()
                )
                commentaries.append(commentary)
                self.last_commentary_time['tsunami'] = datetime.now()
                self.add_to_history(commentary)
            
            # Generate wind commentary
            wind_data = disaster_data.get('wind_data', {})
            if wind_data.get('max_wind_speed', 0) >= 10 and self.should_generate_commentary('wind'):
                commentary_text = await self.generate_wind_commentary(wind_data)
                if commentary_text:
                    commentary = DisasterCommentary(
                        event_type='wind',
                        content=commentary_text,
                        severity='medium',
                        timestamp=datetime.now()
                    )
                    commentaries.append(commentary)
                    self.last_commentary_time['wind'] = datetime.now()
                    self.add_to_history(commentary)
            
            # Generate periodic status update if no events
            if not commentaries and self.should_generate_commentary('status'):
                commentary_text = await self.generate_periodic_status_update()
                commentary = DisasterCommentary(
                    event_type='status',
                    content=commentary_text,
                    severity='low',
                    timestamp=datetime.now()
                )
                commentaries.append(commentary)
                self.last_commentary_time['status'] = datetime.now()
                self.add_to_history(commentary)
            
            return commentaries
        
        except Exception as e:
            logger.error(f"Error generating commentaries: {str(e)}")
            return []
    
    def _determine_earthquake_severity(self, earthquake: Dict[str, Any]) -> str:
        """Determine earthquake severity level"""
        magnitude = earthquake.get('magnitude', 0)
        
        if magnitude >= 7.0:
            return 'critical'
        elif magnitude >= 6.0:
            return 'high'
        elif magnitude >= 5.0:
            return 'medium'
        else:
            return 'low'


class CommentaryBroadcaster:
    """Broadcasts commentary to various outputs (text-to-speech, chat, logs)"""
    
    def __init__(self, commentary_service: AICommentaryService):
        self.commentary_service = commentary_service
        self.is_running = False
        self.broadcast_interval = 300  # 5 minutes
        
    async def start_broadcasting(self):
        """Start continuous commentary broadcasting"""
        self.is_running = True
        logger.info("Started commentary broadcasting")
        
        while self.is_running:
            try:
                # Generate commentaries
                commentaries = await self.commentary_service.generate_commentary_for_current_events()
                
                # Broadcast each commentary
                for commentary in commentaries:
                    await self.broadcast_commentary(commentary)
                    await asyncio.sleep(5)  # Wait between commentaries
                
                # Wait before next cycle
                await asyncio.sleep(self.broadcast_interval)
            
            except Exception as e:
                logger.error(f"Error in commentary broadcasting: {str(e)}")
                await asyncio.sleep(60)
    
    async def broadcast_commentary(self, commentary: DisasterCommentary):
        """
        Broadcast a single commentary
        
        Args:
            commentary: Commentary to broadcast
        """
        logger.info(f"Broadcasting {commentary.event_type} commentary: {commentary.content}")
        
        # Log to file
        with open('commentary_log.txt', 'a', encoding='utf-8') as f:
            timestamp = commentary.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] [{commentary.event_type}] {commentary.content}\n\n")
        
        # TODO: Add text-to-speech here
        # TODO: Send to YouTube Live Chat
        # TODO: Display on screen overlay
    
    def stop_broadcasting(self):
        """Stop commentary broadcasting"""
        self.is_running = False
        logger.info("Stopped commentary broadcasting")


# Singleton instance
_commentary_service = None

def get_commentary_service(openai_api_key: str, backend_url: str = "http://localhost:8000") -> AICommentaryService:
    """Get or create the commentary service singleton"""
    global _commentary_service
    if _commentary_service is None:
        _commentary_service = AICommentaryService(openai_api_key, backend_url)
    return _commentary_service


# Test function
async def test_commentary_service():
    """Test the commentary service"""
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    service = AICommentaryService(api_key)
    
    print("Generating commentaries for current events...")
    commentaries = await service.generate_commentary_for_current_events()
    
    if commentaries:
        print(f"\nGenerated {len(commentaries)} commentaries:")
        for i, commentary in enumerate(commentaries, 1):
            print(f"\n{i}. [{commentary.event_type}] ({commentary.severity})")
            print(f"   {commentary.content}")
    else:
        print("No commentaries generated")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_commentary_service())

