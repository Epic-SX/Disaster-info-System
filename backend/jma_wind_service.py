#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JMA Wind Map Service
Scrapes and processes wind data from Japan Meteorological Agency
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WindData:
    """Wind observation data from a specific location"""
    def __init__(self, location: str, wind_speed: float, wind_direction: str, 
                 observation_time: str, lat: float = None, lon: float = None):
        self.location = location
        self.wind_speed = wind_speed  # m/s
        self.wind_direction = wind_direction
        self.observation_time = observation_time
        self.lat = lat
        self.lon = lon
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "observation_time": self.observation_time,
            "lat": self.lat,
            "lon": self.lon
        }


class JMAWindService:
    """Service to fetch and process JMA wind map data"""
    
    def __init__(self):
        self.base_url = "https://www.jma.go.jp/bosai"
        self.amedas_url = f"{self.base_url}/amedas/data/latest_time.txt"
        self.amedas_data_url = f"{self.base_url}/amedas/data/map"
        self.amedas_table_url = f"{self.base_url}/amedas/const/amedastable.json"
        self.cache = {}
        self.cache_time = None
        self.cache_duration = 600  # 10 minutes
        self.station_info = {}
        logger.info("JMA Wind Service initialized")
    
    async def fetch_station_info(self) -> Dict[str, Any]:
        """Fetch AMeDAS station information"""
        if self.station_info:
            return self.station_info
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.amedas_table_url, timeout=10) as response:
                    if response.status == 200:
                        self.station_info = await response.json()
                        logger.info(f"Loaded {len(self.station_info)} AMeDAS stations")
                        return self.station_info
                    else:
                        logger.error(f"Failed to fetch station info: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching station info: {str(e)}")
            return {}
    
    async def fetch_latest_time(self) -> Optional[str]:
        """Fetch the latest observation time"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.amedas_url, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        return text.strip()
                    else:
                        logger.error(f"Failed to fetch latest time: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching latest time: {str(e)}")
            return None
    
    async def fetch_wind_data(self, observation_time: str) -> Dict[str, Any]:
        """Fetch wind data for a specific observation time"""
        url = f"{self.amedas_data_url}/{observation_time}.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"Failed to fetch wind data: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching wind data: {str(e)}")
            return {}
    
    async def get_current_wind_data(self, force_refresh: bool = False) -> List[WindData]:
        """Get current wind data from all AMeDAS stations"""
        # Check cache
        if not force_refresh and self.cache and self.cache_time:
            age = (datetime.now() - self.cache_time).total_seconds()
            if age < self.cache_duration:
                logger.debug(f"Returning cached wind data (age: {age}s)")
                return self.cache.get('wind_data', [])
        
        try:
            # Fetch station info if not already loaded
            if not self.station_info:
                await self.fetch_station_info()
            
            # Get latest observation time
            latest_time = await self.fetch_latest_time()
            if not latest_time:
                logger.warning("Could not determine latest observation time")
                return []
            
            # Fetch wind data
            raw_data = await self.fetch_wind_data(latest_time)
            if not raw_data:
                logger.warning("No wind data available")
                return []
            
            # Process wind data
            wind_data_list = []
            for station_id, station_data in raw_data.items():
                if 'wind' not in station_data:
                    continue
                
                wind = station_data.get('wind', {})
                if not wind:
                    continue
                
                # Get station information
                station_info = self.station_info.get(station_id, {})
                location = station_info.get('kjName', station_id)
                lat = station_info.get('lat', [None])[0] if 'lat' in station_info else None
                lon = station_info.get('lon', [None])[0] if 'lon' in station_info else None
                
                # Extract wind data
                wind_speed = wind.get('windSpeed', [None])[0] if 'windSpeed' in wind else None
                wind_direction = wind.get('windDirection', [None])[0] if 'windDirection' in wind else None
                
                if wind_speed is not None:
                    # Convert wind direction from degrees to cardinal direction
                    wind_dir_str = self._degrees_to_direction(wind_direction) if wind_direction is not None else "不明"
                    
                    wind_data = WindData(
                        location=location,
                        wind_speed=wind_speed,
                        wind_direction=wind_dir_str,
                        observation_time=latest_time,
                        lat=lat,
                        lon=lon
                    )
                    wind_data_list.append(wind_data)
            
            # Update cache
            self.cache = {
                'wind_data': wind_data_list,
                'observation_time': latest_time
            }
            self.cache_time = datetime.now()
            
            logger.info(f"Fetched wind data for {len(wind_data_list)} stations")
            return wind_data_list
        
        except Exception as e:
            logger.error(f"Error getting current wind data: {str(e)}")
            return []
    
    def _degrees_to_direction(self, degrees: float) -> str:
        """Convert wind direction in degrees to cardinal direction"""
        if degrees is None:
            return "不明"
        
        directions = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
                     "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
        
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    async def get_wind_summary(self) -> Dict[str, Any]:
        """Get summary of wind conditions"""
        wind_data_list = await self.get_current_wind_data()
        
        if not wind_data_list:
            return {
                "status": "no_data",
                "message": "風況データが取得できません"
            }
        
        # Calculate statistics
        wind_speeds = [w.wind_speed for w in wind_data_list if w.wind_speed is not None]
        
        if not wind_speeds:
            return {
                "status": "no_data",
                "message": "風速データがありません"
            }
        
        avg_speed = sum(wind_speeds) / len(wind_speeds)
        max_speed = max(wind_speeds)
        max_wind_location = max(wind_data_list, key=lambda x: x.wind_speed if x.wind_speed else 0)
        
        # Categorize wind strength
        if max_speed >= 15:
            alert_level = "強風警戒"
            alert_color = "red"
        elif max_speed >= 10:
            alert_level = "風やや強い"
            alert_color = "orange"
        elif max_speed >= 5:
            alert_level = "通常"
            alert_color = "green"
        else:
            alert_level = "穏やか"
            alert_color = "blue"
        
        return {
            "status": "ok",
            "observation_time": wind_data_list[0].observation_time if wind_data_list else None,
            "total_stations": len(wind_data_list),
            "average_wind_speed": round(avg_speed, 1),
            "max_wind_speed": round(max_speed, 1),
            "max_wind_location": max_wind_location.location,
            "max_wind_direction": max_wind_location.wind_direction,
            "alert_level": alert_level,
            "alert_color": alert_color,
            "top_10_windy_locations": [
                {
                    "location": w.location,
                    "wind_speed": w.wind_speed,
                    "wind_direction": w.wind_direction,
                    "lat": w.lat,
                    "lon": w.lon
                }
                for w in sorted(wind_data_list, key=lambda x: x.wind_speed if x.wind_speed else 0, reverse=True)[:10]
            ]
        }
    
    async def get_wind_map_data(self) -> Dict[str, Any]:
        """Get wind data formatted for map display"""
        wind_data_list = await self.get_current_wind_data()
        
        return {
            "type": "FeatureCollection",
            "observation_time": wind_data_list[0].observation_time if wind_data_list else None,
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [w.lon, w.lat] if w.lon and w.lat else None
                    },
                    "properties": {
                        "location": w.location,
                        "wind_speed": w.wind_speed,
                        "wind_direction": w.wind_direction,
                        "observation_time": w.observation_time
                    }
                }
                for w in wind_data_list if w.lat and w.lon
            ]
        }


# Singleton instance
_wind_service = None

def get_wind_service() -> JMAWindService:
    """Get or create the wind service singleton"""
    global _wind_service
    if _wind_service is None:
        _wind_service = JMAWindService()
    return _wind_service


# Test function
async def test_wind_service():
    """Test the wind service"""
    service = get_wind_service()
    
    print("Fetching current wind data...")
    wind_data = await service.get_current_wind_data()
    print(f"Retrieved {len(wind_data)} stations")
    
    if wind_data:
        print("\nTop 10 windiest locations:")
        for i, w in enumerate(sorted(wind_data, key=lambda x: x.wind_speed if x.wind_speed else 0, reverse=True)[:10], 1):
            print(f"{i}. {w.location}: {w.wind_speed}m/s {w.wind_direction}")
    
    print("\nWind summary:")
    summary = await service.get_wind_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_wind_service())

