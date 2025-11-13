#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Disaster API Service
Integrates multiple disaster data sources including P2P earthquake, J-SHIS, and IIJ APIs
"""

import os
import json
import logging
import asyncio
import websockets
import requests
import aiohttp
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DisasterType(Enum):
    EARTHQUAKE = "earthquake"
    TSUNAMI = "tsunami"
    TYPHOON = "typhoon"
    FLOOD = "flood"
    VOLCANO = "volcano"
    OTHER = "other"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ADVISORY = "advisory"
    CRITICAL = "critical"

@dataclass
class EarthquakeInfo:
    """Earthquake information data class"""
    id: str
    magnitude: float
    depth: float
    latitude: float
    longitude: float
    location: str
    timestamp: datetime
    intensity: Optional[str] = None
    tsunami_warning: bool = False
    source: str = "unknown"

@dataclass
class TsunamiInfo:
    """Tsunami information data class"""
    id: str
    area: str
    height_prediction: float
    arrival_time: Optional[datetime]
    alert_level: AlertLevel
    timestamp: datetime
    source: str = "unknown"

@dataclass
class DisasterAlert:
    """General disaster alert data class"""
    id: str
    disaster_type: DisasterType
    title: str
    description: str
    location: str
    coordinates: Optional[Dict[str, float]]
    alert_level: AlertLevel
    timestamp: datetime
    expiry_time: Optional[datetime]
    source: str
    additional_info: Optional[Dict] = None

class P2PEarthquakeAPI:
    """P2P地震情報 API integration"""
    
    def __init__(self):
        self.base_url = os.getenv('P2P_EARTHQUAKE_API', 'https://api.p2pquake.net/v2')
        
    def _parse_p2p_datetime(self, time_str: str) -> datetime:
        """Parse P2P API datetime format (e.g., '2025/11/12 21:29:38.23')"""
        try:
            # P2P API format: YYYY/MM/DD HH:MM:SS.mmm
            # Replace slashes with dashes for ISO format
            time_str = time_str.replace('/', '-')
            
            # Handle varying decimal places in seconds
            if '.' in time_str:
                # Ensure exactly 6 decimal places for microseconds
                parts = time_str.split('.')
                if len(parts) == 2:
                    # Pad or truncate to 6 digits
                    decimal_part = parts[1][:6].ljust(6, '0')
                    time_str = f"{parts[0]}.{decimal_part}"
            
            return datetime.fromisoformat(time_str)
        except Exception as e:
            logger.warning(f"Error parsing P2P datetime '{time_str}': {e}, using current time")
            return datetime.now()
        
    async def get_latest_earthquakes(self, limit: int = 10) -> List[EarthquakeInfo]:
        """Get latest earthquake information from P2P"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/history"
                params = {
                    'codes': '551',  # Earthquake information code
                    'limit': limit
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        earthquakes = []
                        
                        for item in data:
                            try:
                                earthquake_data = item.get('earthquake', {})
                                hypocenter = earthquake_data.get('hypocenter', {})
                                
                                earthquake = EarthquakeInfo(
                                    id=str(item.get('id', '')),
                                    magnitude=float(hypocenter.get('magnitude', 0)),
                                    depth=float(hypocenter.get('depth', 0)),
                                    latitude=float(hypocenter.get('latitude', 0)),
                                    longitude=float(hypocenter.get('longitude', 0)),
                                    location=hypocenter.get('name', ''),
                                    timestamp=self._parse_p2p_datetime(item.get('time', '')),
                                    intensity=earthquake_data.get('maxScale', ''),
                                    tsunami_warning=earthquake_data.get('domesticTsunami', '') != 'None',
                                    source='P2P地震情報'
                                )
                                earthquakes.append(earthquake)
                            except Exception as e:
                                logger.warning(f"Error parsing P2P earthquake data: {e}")
                                continue
                        
                        return earthquakes
                    else:
                        logger.error(f"P2P API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching P2P earthquake data: {e}")
            return []
    
    async def get_tsunami_info(self) -> List[TsunamiInfo]:
        """Get tsunami information from P2P"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/history"
                params = {
                    'codes': '552',  # Tsunami information code
                    'limit': 5
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        tsunami_alerts = []
                        
                        for item in data:
                            try:
                                areas = item.get('areas', [])
                                for area in areas:
                                    tsunami = TsunamiInfo(
                                        id=str(item.get('id', '')),
                                        area=area.get('name', ''),
                                        height_prediction=float(area.get('category', {}).get('height', 0)),
                                        arrival_time=None,  # Not provided in this API
                                        alert_level=self._convert_tsunami_grade(area.get('grade', '')),
                                        timestamp=self._parse_p2p_datetime(item.get('time', '')),
                                        source='P2P地震情報'
                                    )
                                    tsunami_alerts.append(tsunami)
                            except Exception as e:
                                logger.warning(f"Error parsing P2P tsunami data: {e}")
                                continue
                        
                        return tsunami_alerts
                    else:
                        logger.error(f"P2P API tsunami error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching P2P tsunami data: {e}")
            return []
    
    def _convert_tsunami_grade(self, grade: str) -> AlertLevel:
        """Convert P2P tsunami grade to alert level"""
        grade_mapping = {
            'MajorWarning': AlertLevel.CRITICAL,
            'Warning': AlertLevel.WARNING,
            'Watch': AlertLevel.ADVISORY,
            'Unknown': AlertLevel.INFO
        }
        return grade_mapping.get(grade, AlertLevel.INFO)

class JSHISMapAPI:
    """J-SHIS Map API integration for seismic hazard information"""
    
    def __init__(self):
        self.base_url = os.getenv('J_SHIS_API_BASE', 'https://www.j-shis.bosai.go.jp/map')
        
    async def get_seismic_hazard_info(self, latitude: float, longitude: float) -> Dict:
        """Get seismic hazard information for specific coordinates"""
        try:
            # J-SHIS API endpoint for hazard map data
            # Note: This is a simplified implementation - actual J-SHIS API may require different parameters
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/hazard"
                params = {
                    'lat': latitude,
                    'lon': longitude,
                    'meshcode': 1  # Example mesh code
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"J-SHIS API error: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error fetching J-SHIS data: {e}")
            return {}
    
    async def get_active_faults(self, region: str = None) -> List[Dict]:
        """Get active fault information"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/faults"
                params = {}
                if region:
                    params['region'] = region
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"J-SHIS faults API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching J-SHIS fault data: {e}")
            return []

class IIJEarthquakeWebSocket:
    """IIJ Engineering Earthquake WebSocket API integration"""
    
    def __init__(self):
        self.websocket_url = os.getenv('IIJ_EARTHQUAKE_WEBSOCKET', 'wss://ws-api.iij.jp/v1/earthquake')
        self.connection = None
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add callback function for earthquake alerts"""
        self.callbacks.append(callback)
    
    async def connect(self):
        """Connect to IIJ earthquake WebSocket"""
        try:
            self.connection = await websockets.connect(self.websocket_url)
            logger.info("Connected to IIJ earthquake WebSocket")
            
            # Start listening for messages
            await self._listen_for_messages()
            
        except Exception as e:
            logger.error(f"Error connecting to IIJ WebSocket: {e}")
    
    async def _listen_for_messages(self):
        """Listen for incoming earthquake messages"""
        try:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    await self._process_earthquake_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing IIJ message: {e}")
                except Exception as e:
                    logger.error(f"Error processing IIJ message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("IIJ WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in IIJ WebSocket listener: {e}")
    
    async def _process_earthquake_message(self, data: Dict):
        """Process earthquake message from IIJ WebSocket"""
        try:
            earthquake = EarthquakeInfo(
                id=str(data.get('id', '')),
                magnitude=float(data.get('magnitude', 0)),
                depth=float(data.get('depth', 0)),
                latitude=float(data.get('latitude', 0)),
                longitude=float(data.get('longitude', 0)),
                location=data.get('location', ''),
                timestamp=datetime.fromisoformat(data.get('timestamp', '')),
                intensity=data.get('intensity', ''),
                tsunami_warning=data.get('tsunami', False),
                source='IIJ Engineering'
            )
            
            # Call all registered callbacks
            for callback in self.callbacks:
                try:
                    await callback(earthquake)
                except Exception as e:
                    logger.error(f"Error in IIJ callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing IIJ earthquake message: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from IIJ earthquake WebSocket")

class DisasterAPIService:
    """Main disaster API service coordinating all data sources"""
    
    def __init__(self):
        self.p2p_api = P2PEarthquakeAPI()
        self.jshis_api = JSHISMapAPI()
        self.iij_websocket = IIJEarthquakeWebSocket()
        self.db_path = "disaster_data.db"
        
        # Initialize database
        self._init_database()
        
        # Setup IIJ WebSocket callback
        self.iij_websocket.add_callback(self._handle_realtime_earthquake)
    
    def _init_database(self):
        """Initialize disaster data database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS earthquakes (
                id TEXT PRIMARY KEY,
                magnitude REAL,
                depth REAL,
                latitude REAL,
                longitude REAL,
                location TEXT,
                timestamp DATETIME,
                intensity TEXT,
                tsunami_warning BOOLEAN,
                source TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disaster_alerts (
                id TEXT PRIMARY KEY,
                disaster_type TEXT,
                title TEXT,
                description TEXT,
                location TEXT,
                alert_level TEXT,
                timestamp DATETIME,
                expiry_time DATETIME,
                source TEXT,
                additional_info TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def get_comprehensive_earthquake_data(self) -> List[EarthquakeInfo]:
        """Get earthquake data from all sources"""
        all_earthquakes = []
        
        # Get data from P2P API
        p2p_earthquakes = await self.p2p_api.get_latest_earthquakes()
        all_earthquakes.extend(p2p_earthquakes)
        
        # Remove duplicates based on timestamp and location
        unique_earthquakes = self._remove_duplicate_earthquakes(all_earthquakes)
        
        # Save to database
        for earthquake in unique_earthquakes:
            await self._save_earthquake(earthquake)
        
        return unique_earthquakes
    
    async def get_tsunami_alerts(self) -> List[TsunamiInfo]:
        """Get tsunami alerts from all sources"""
        tsunami_alerts = await self.p2p_api.get_tsunami_info()
        return tsunami_alerts
    
    async def start_realtime_monitoring(self):
        """Start real-time monitoring via WebSocket"""
        try:
            await self.iij_websocket.connect()
        except Exception as e:
            logger.error(f"Error starting real-time monitoring: {e}")
    
    async def _handle_realtime_earthquake(self, earthquake: EarthquakeInfo):
        """Handle real-time earthquake data from WebSocket"""
        try:
            await self._save_earthquake(earthquake)
            logger.info(f"Real-time earthquake: M{earthquake.magnitude} at {earthquake.location}")
            
            # Check if this is a significant earthquake
            if earthquake.magnitude >= 5.0:
                await self._create_earthquake_alert(earthquake)
                
        except Exception as e:
            logger.error(f"Error handling real-time earthquake: {e}")
    
    async def _save_earthquake(self, earthquake: EarthquakeInfo):
        """Save earthquake data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO earthquakes 
                (id, magnitude, depth, latitude, longitude, location, timestamp, intensity, tsunami_warning, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                earthquake.id,
                earthquake.magnitude,
                earthquake.depth,
                earthquake.latitude,
                earthquake.longitude,
                earthquake.location,
                earthquake.timestamp,
                earthquake.intensity,
                earthquake.tsunami_warning,
                earthquake.source
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving earthquake data: {e}")
    
    async def _create_earthquake_alert(self, earthquake: EarthquakeInfo):
        """Create disaster alert for significant earthquake"""
        try:
            alert = DisasterAlert(
                id=f"eq_{earthquake.id}",
                disaster_type=DisasterType.EARTHQUAKE,
                title=f"地震発生 M{earthquake.magnitude}",
                description=f"マグニチュード{earthquake.magnitude}の地震が{earthquake.location}で発生しました。",
                location=earthquake.location,
                coordinates={
                    'latitude': earthquake.latitude,
                    'longitude': earthquake.longitude
                },
                alert_level=self._determine_earthquake_alert_level(earthquake.magnitude),
                timestamp=earthquake.timestamp,
                expiry_time=earthquake.timestamp + timedelta(hours=24),
                source=earthquake.source,
                additional_info=asdict(earthquake)
            )
            
            await self._save_disaster_alert(alert)
            
        except Exception as e:
            logger.error(f"Error creating earthquake alert: {e}")
    
    def _determine_earthquake_alert_level(self, magnitude: float) -> AlertLevel:
        """Determine alert level based on earthquake magnitude"""
        if magnitude >= 7.0:
            return AlertLevel.CRITICAL
        elif magnitude >= 6.0:
            return AlertLevel.WARNING
        elif magnitude >= 5.0:
            return AlertLevel.ADVISORY
        else:
            return AlertLevel.INFO
    
    async def _save_disaster_alert(self, alert: DisasterAlert):
        """Save disaster alert to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO disaster_alerts 
                (id, disaster_type, title, description, location, alert_level, timestamp, expiry_time, source, additional_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id,
                alert.disaster_type.value,
                alert.title,
                alert.description,
                alert.location,
                alert.alert_level.value,
                alert.timestamp,
                alert.expiry_time,
                alert.source,
                json.dumps(alert.additional_info) if alert.additional_info else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving disaster alert: {e}")
    
    def _remove_duplicate_earthquakes(self, earthquakes: List[EarthquakeInfo]) -> List[EarthquakeInfo]:
        """Remove duplicate earthquakes based on similarity"""
        unique_earthquakes = []
        
        for earthquake in earthquakes:
            is_duplicate = False
            for existing in unique_earthquakes:
                # Check if earthquakes are similar (same time window and close location)
                time_diff = abs((earthquake.timestamp - existing.timestamp).total_seconds())
                if (time_diff < 300 and  # Within 5 minutes
                    abs(earthquake.latitude - existing.latitude) < 0.1 and
                    abs(earthquake.longitude - existing.longitude) < 0.1):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_earthquakes.append(earthquake)
        
        return unique_earthquakes
    
    async def get_recent_alerts(self, hours: int = 24) -> List[DisasterAlert]:
        """Get recent disaster alerts from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT * FROM disaster_alerts 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            ''', (since_time,))
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alert = DisasterAlert(
                    id=row[0],
                    disaster_type=DisasterType(row[1]),
                    title=row[2],
                    description=row[3],
                    location=row[4],
                    alert_level=AlertLevel(row[5]),
                    timestamp=datetime.fromisoformat(row[6]),
                    expiry_time=datetime.fromisoformat(row[7]) if row[7] else None,
                    source=row[8],
                    additional_info=json.loads(row[9]) if row[9] else None
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []

# Example usage
async def main():
    """Test the disaster API service"""
    service = DisasterAPIService()
    
    print("Testing comprehensive earthquake data...")
    earthquakes = await service.get_comprehensive_earthquake_data()
    print(f"Found {len(earthquakes)} earthquakes")
    
    for eq in earthquakes[:3]:
        print(f"- M{eq.magnitude} at {eq.location} ({eq.source})")
    
    print("\nTesting tsunami alerts...")
    tsunami_alerts = await service.get_tsunami_alerts()
    print(f"Found {len(tsunami_alerts)} tsunami alerts")
    
    for alert in tsunami_alerts[:2]:
        print(f"- {alert.area}: {alert.alert_level.value}")
    
    print("\nTesting recent alerts...")
    recent_alerts = await service.get_recent_alerts()
    print(f"Found {len(recent_alerts)} recent alerts")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 