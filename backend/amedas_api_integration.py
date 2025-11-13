#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AMeDAS API Integration
FastAPI endpoints for serving AMeDAS weather data from JSON file
"""

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import json
from pathlib import Path

from amedas_scheduler import get_scheduler

logger = logging.getLogger(__name__)

# JSON file path
AMEDAS_JSON_PATH = "amedas_data.json"


def load_amedas_data() -> List[Dict[str, Any]]:
    """Load AMeDAS data from JSON file"""
    try:
        json_path = Path(AMEDAS_JSON_PATH)
        if not json_path.exists():
            logger.warning(f"AMeDAS data file not found: {AMEDAS_JSON_PATH}")
            return []
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Error loading AMeDAS data from JSON: {e}")
        return []


# FastAPI routes (add these to your existing main.py)

async def get_amedas_latest(prefecture_code: Optional[str] = None):
    """
    Get latest AMeDAS observations
    
    Args:
        prefecture_code: Optional prefecture code (e.g., "010000" for Hokkaido)
    
    Returns:
        Latest weather observations
    """
    try:
        data = load_amedas_data()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Filter by prefecture if specified
        if prefecture_code:
            data = [region for region in data if region.get('prefecture_code') == prefecture_code]
        
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"No data available for prefecture code: {prefecture_code}" if prefecture_code else "No data available"
            )
        
        # Count observations
        total_observations = sum(len(region.get('observations', [])) for region in data)
        
        return {
            'success': True,
            'prefecture_code': prefecture_code,
            'regions_count': len(data),
            'observations_count': total_observations,
            'data': data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest observations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_amedas_statistics():
    """Get AMeDAS data statistics"""
    try:
        data = load_amedas_data()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate statistics
        total_regions = len(data)
        total_observations = sum(len(region.get('observations', [])) for region in data)
        observation_time = data[0].get('observation_time') if data else None
        
        # Count unique stations
        unique_stations = set()
        for region in data:
            for obs in region.get('observations', []):
                unique_stations.add(obs.get('location_id'))
        
        stats = {
            'total_regions': total_regions,
            'total_observations': total_observations,
            'unique_stations': len(unique_stations),
            'latest_observation_time': observation_time,
            'data_source': 'JSON file',
            'file_path': AMEDAS_JSON_PATH
        }
        
        return {
            'success': True,
            'statistics': stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_amedas_prefecture(prefecture_code: str):
    """
    Get AMeDAS data for specific prefecture
    
    Args:
        prefecture_code: Prefecture code (e.g., "010000" for Hokkaido)
    """
    try:
        data = load_amedas_data()
        
        # Filter by prefecture code
        prefecture_data = [region for region in data if region.get('prefecture_code') == prefecture_code]
        
        if not prefecture_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No data available for prefecture code: {prefecture_code}"
            )
        
        # Collect all observations
        all_observations = []
        observation_time = None
        for region in prefecture_data:
            if not observation_time:
                observation_time = region.get('observation_time')
            all_observations.extend(region.get('observations', []))
        
        return {
            'success': True,
            'prefecture_code': prefecture_code,
            'observation_time': observation_time,
            'regions_count': len(prefecture_data),
            'observations_count': len(all_observations),
            'regions': prefecture_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prefecture data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_amedas_extremes():
    """Get extreme weather conditions (hottest, coldest, windiest)"""
    try:
        data = load_amedas_data()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Collect all observations
        all_observations = []
        observation_time = None
        for region in data:
            if not observation_time:
                observation_time = region.get('observation_time')
            all_observations.extend(region.get('observations', []))
        
        if not all_observations:
            raise HTTPException(status_code=404, detail="No observations available")
        
        # Find extremes
        coldest = None
        hottest = None
        windiest = None
        rainiest = None
        
        for obs in all_observations:
            # Parse temperature
            temp_str = obs.get('temperature')
            if temp_str and temp_str != '---':
                try:
                    temp = float(temp_str)
                    if coldest is None or temp < coldest.get('temperature_value', float('inf')):
                        coldest = {**obs, 'temperature_value': temp}
                    if hottest is None or temp > hottest.get('temperature_value', float('-inf')):
                        hottest = {**obs, 'temperature_value': temp}
                except (ValueError, TypeError):
                    pass
            
            # Parse wind speed
            wind_str = obs.get('wind_speed')
            if wind_str and wind_str != '---':
                try:
                    wind = float(wind_str)
                    if windiest is None or wind > windiest.get('wind_speed_value', float('-inf')):
                        windiest = {**obs, 'wind_speed_value': wind}
                except (ValueError, TypeError):
                    pass
            
            # Parse precipitation
            precip_str = obs.get('precipitation_1h')
            if precip_str and precip_str != '---':
                try:
                    precip = float(precip_str)
                    if precip > 0:
                        if rainiest is None or precip > rainiest.get('precipitation_value', float('-inf')):
                            rainiest = {**obs, 'precipitation_value': precip}
                except (ValueError, TypeError):
                    pass
        
        return {
            'success': True,
            'observation_time': observation_time,
            'coldest': {
                'location': coldest['location_name'],
                'temperature': coldest['temperature'],
                'region': coldest['region_name']
            } if coldest else None,
            'hottest': {
                'location': hottest['location_name'],
                'temperature': hottest['temperature'],
                'region': hottest['region_name']
            } if hottest else None,
            'windiest': {
                'location': windiest['location_name'],
                'wind_speed': windiest['wind_speed'],
                'wind_direction': windiest['wind_direction'],
                'region': windiest['region_name']
            } if windiest else None,
            'rainiest': {
                'location': rainiest['location_name'],
                'precipitation': rainiest['precipitation_1h'],
                'region': rainiest['region_name']
            } if rainiest else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extremes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_amedas_alerts(
    temperature_min: Optional[float] = None,
    temperature_max: Optional[float] = None,
    wind_speed_min: Optional[float] = None,
    precipitation_min: Optional[float] = None
):
    """
    Get weather alerts based on thresholds
    
    Args:
        temperature_min: Alert if temperature below this (°C)
        temperature_max: Alert if temperature above this (°C)
        wind_speed_min: Alert if wind speed above this (m/s)
        precipitation_min: Alert if precipitation above this (mm)
    """
    try:
        data = load_amedas_data()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Collect all observations
        all_observations = []
        observation_time = None
        for region in data:
            if not observation_time:
                observation_time = region.get('observation_time')
            all_observations.extend(region.get('observations', []))
        
        if not all_observations:
            raise HTTPException(status_code=404, detail="No observations available")
        
        alerts = []
        
        for obs in all_observations:
            alert_reasons = []
            
            # Temperature alerts
            temp_str = obs.get('temperature')
            if temp_str and temp_str != '---':
                try:
                    temp = float(temp_str)
                    if temperature_min is not None and temp < temperature_min:
                        alert_reasons.append(f"Temperature {temp}°C below threshold {temperature_min}°C")
                    if temperature_max is not None and temp > temperature_max:
                        alert_reasons.append(f"Temperature {temp}°C above threshold {temperature_max}°C")
                except (ValueError, TypeError):
                    pass
            
            # Wind speed alerts
            wind_str = obs.get('wind_speed')
            if wind_str and wind_str != '---' and wind_speed_min is not None:
                try:
                    wind = float(wind_str)
                    if wind > wind_speed_min:
                        alert_reasons.append(f"Wind speed {wind}m/s above threshold {wind_speed_min}m/s")
                except (ValueError, TypeError):
                    pass
            
            # Precipitation alerts
            precip_str = obs.get('precipitation_1h')
            if precip_str and precip_str != '---' and precipitation_min is not None:
                try:
                    precip = float(precip_str)
                    if precip > precipitation_min:
                        alert_reasons.append(f"Precipitation {precip}mm above threshold {precipitation_min}mm")
                except (ValueError, TypeError):
                    pass
            
            if alert_reasons:
                alerts.append({
                    'location': obs['location_name'],
                    'region': obs['region_name'],
                    'temperature': obs.get('temperature'),
                    'wind_speed': obs.get('wind_speed'),
                    'wind_direction': obs.get('wind_direction'),
                    'precipitation_1h': obs.get('precipitation_1h'),
                    'observation_time': obs.get('observation_time'),
                    'alert_reasons': alert_reasons
                })
        
        return {
            'success': True,
            'observation_time': observation_time,
            'alerts_count': len(alerts),
            'thresholds': {
                'temperature_min': temperature_min,
                'temperature_max': temperature_max,
                'wind_speed_min': wind_speed_min,
                'precipitation_min': precipitation_min
            },
            'alerts': alerts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example: How to add these to your existing main.py:
"""
from amedas_api_integration import (
    get_amedas_latest,
    get_amedas_statistics,
    get_amedas_prefecture,
    get_amedas_extremes,
    get_amedas_alerts,
    AMEDAS_JSON_PATH
)

# Add these routes to your FastAPI app:

@app.get("/api/amedas/latest")
async def api_amedas_latest(prefecture_code: Optional[str] = Query(None, description="Prefecture code (e.g., '010000' for Hokkaido)")):
    return await get_amedas_latest(prefecture_code)

@app.get("/api/amedas/statistics")
async def api_amedas_statistics():
    return await get_amedas_statistics()

@app.get("/api/amedas/prefecture/{prefecture_code}")
async def api_amedas_prefecture(prefecture_code: str):
    return await get_amedas_prefecture(prefecture_code)

@app.get("/api/amedas/extremes")
async def api_amedas_extremes():
    return await get_amedas_extremes()

@app.get("/api/amedas/alerts")
async def api_amedas_alerts(
    temperature_min: Optional[float] = Query(None, description="Alert if temperature below this (°C)"),
    temperature_max: Optional[float] = Query(None, description="Alert if temperature above this (°C)"),
    wind_speed_min: Optional[float] = Query(None, description="Alert if wind speed above this (m/s)"),
    precipitation_min: Optional[float] = Query(None, description="Alert if precipitation above this (mm)")
):
    return await get_amedas_alerts(
        temperature_min=temperature_min,
        temperature_max=temperature_max,
        wind_speed_min=wind_speed_min,
        precipitation_min=precipitation_min
    )

Note: Make sure to set the correct JSON file path by updating AMEDAS_JSON_PATH if needed.
"""


