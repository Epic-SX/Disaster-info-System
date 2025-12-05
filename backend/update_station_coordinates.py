#!/usr/bin/env python3
"""
Script to update AMeDAS station coordinates from JMA API
This will fetch all available station coordinates and update the amedas_station_coordinates.json file
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JMA API URL for station table
STATION_TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
OUTPUT_FILE = "amedas_station_coordinates.json"


async def fetch_station_table() -> Dict[str, Any]:
    """Fetch the complete station table from JMA API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STATION_TABLE_URL, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched station table with {len(data)} stations")
                    return data
                else:
                    logger.error(f"Failed to fetch station table: HTTP {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Error fetching station table: {e}")
        return {}


def extract_coordinates(station_table: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Extract station coordinates from the station table
    
    Args:
        station_table: Raw station table from JMA API
        
    Returns:
        Dictionary mapping station name to {lat, lng}
    """
    coordinates = {}
    
    for station_id, station_info in station_table.items():
        # Get station name (Japanese Kanji name)
        station_name = station_info.get("kjName")
        
        # Get coordinates (lat/lon)
        lat_list = station_info.get("lat")
        lon_list = station_info.get("lon")
        
        if station_name and lat_list and lon_list:
            # JMA provides coordinates as [degrees, minutes, seconds]
            # Convert to decimal degrees
            try:
                # lat and lon are in the format [degrees, minutes, seconds]
                lat_decimal = lat_list[0] + lat_list[1] / 60.0
                if len(lat_list) > 2:
                    lat_decimal += lat_list[2] / 3600.0
                
                lon_decimal = lon_list[0] + lon_list[1] / 60.0
                if len(lon_list) > 2:
                    lon_decimal += lon_list[2] / 3600.0
                
                coordinates[station_name] = {
                    "lat": round(lat_decimal, 4),
                    "lng": round(lon_decimal, 4)
                }
                
            except (IndexError, TypeError, ValueError) as e:
                logger.warning(f"Could not parse coordinates for station {station_name} (ID: {station_id}): {e}")
                continue
    
    logger.info(f"Extracted coordinates for {len(coordinates)} stations")
    return coordinates


async def update_coordinates_file():
    """Main function to update the coordinates file"""
    logger.info("Starting station coordinates update...")
    
    # Fetch station table from JMA
    station_table = await fetch_station_table()
    
    if not station_table:
        logger.error("Failed to fetch station table. Exiting.")
        return False
    
    # Extract coordinates
    coordinates = extract_coordinates(station_table)
    
    if not coordinates:
        logger.error("No coordinates extracted. Exiting.")
        return False
    
    # Save to JSON file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(coordinates, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Successfully saved {len(coordinates)} station coordinates to {OUTPUT_FILE}")
        
        # Display some statistics
        logger.info("\n" + "="*50)
        logger.info("Station Coordinates Update Summary")
        logger.info("="*50)
        logger.info(f"Total stations with coordinates: {len(coordinates)}")
        logger.info(f"Output file: {OUTPUT_FILE}")
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving coordinates file: {e}")
        return False


async def main():
    """Entry point"""
    success = await update_coordinates_file()
    
    if success:
        logger.info("\n✓ Coordinates file updated successfully!")
        logger.info("You can now restart your backend server to use the updated coordinates.")
    else:
        logger.error("\n✗ Failed to update coordinates file.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)


