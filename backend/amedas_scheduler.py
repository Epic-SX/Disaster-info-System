#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AMeDAS Scheduler Service
Automatically updates AMeDAS data every hour and stores in JSON file
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import signal
import sys

from jma_amedas_scraper import get_amedas_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AMeDASScheduler:
    """Scheduler for automatic AMeDAS data updates"""
    
    def __init__(self, update_interval: int = 3600, json_path: str = "amedas_data.json"):
        """
        Initialize scheduler
        
        Args:
            update_interval: Update interval in seconds (default: 3600 = 1 hour)
            json_path: Path to JSON file for data export (default: "amedas_data.json")
        
        Note:
            This scheduler fetches data from JMA and exports to JSON file.
        """
        self.service = get_amedas_service()
        self.update_interval = update_interval
        self.json_path = json_path
        self.running = False
        self.task = None
        self.update_history = []  # Store recent update logs in memory
        
        logger.info(f"Scheduler initialized with {update_interval}s interval")
        logger.info(f"JSON export path: {json_path}")
    
    async def fetch_and_store(self) -> dict:
        """Fetch latest AMeDAS data and export to JSON"""
        try:
            logger.info("Fetching latest AMeDAS data from JMA...")
            
            # Fetch data from JMA API
            data = await self.service.get_all_data(force_refresh=True)
            
            if not data:
                logger.error("No data received from API")
                self._log_update(None, 0, 0, 'error', 'No data received')
                return {
                    'success': False,
                    'message': 'No data received',
                    'observations': 0
                }
            
            # Count observations
            observation_time = data[0]['observation_time'] if data else None
            total_obs = sum(len(region['observations']) for region in data)
            regions_count = len(data)
            
            # Export to JSON
            logger.info(f"Exporting {total_obs} observations to {self.json_path}...")
            filename = await self.service.export_to_json(filename=self.json_path)
            
            # Log the update
            if observation_time:
                self._log_update(
                    observation_time=observation_time,
                    obs_count=total_obs,
                    regions_count=regions_count,
                    status='success',
                    message=f"Updated {total_obs} observations from {regions_count} regions"
                )
            
            return {
                'success': True,
                'observations': total_obs,
                'regions': regions_count,
                'observation_time': observation_time,
                'export_method': 'json',
                'export_path': filename
            }
            
        except Exception as e:
            logger.error(f"Error fetching and storing data: {e}", exc_info=True)
            
            # Log the error
            self._log_update(
                observation_time=datetime.now().isoformat(),
                obs_count=0,
                regions_count=0,
                status='error',
                message=str(e)
            )
            
            return {
                'success': False,
                'message': str(e),
                'observations': 0
            }
    
    def _log_update(self, observation_time: Optional[str], obs_count: int, 
                    regions_count: int, status: str, message: str):
        """Log an update operation in memory"""
        log_entry = {
            'update_time': observation_time or datetime.now().isoformat(),
            'observations_count': obs_count,
            'regions_count': regions_count,
            'status': status,
            'message': message,
            'created_at': datetime.now().isoformat()
        }
        self.update_history.append(log_entry)
        
        # Keep only last 50 entries
        if len(self.update_history) > 50:
            self.update_history = self.update_history[-50:]
    
    async def update_loop(self):
        """Main update loop"""
        logger.info(f"Starting update loop (interval: {self.update_interval}s = {self.update_interval/3600:.1f}h)")
        
        self.running = True
        
        # Do initial update immediately
        logger.info("Performing initial update...")
        await self.fetch_and_store()
        
        # Calculate next update time (on the hour)
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        
        logger.info(f"Next update scheduled at {next_hour.strftime('%H:%M:%S')} ({wait_seconds/60:.1f} minutes)")
        
        while self.running:
            try:
                # Wait until next update time
                await asyncio.sleep(wait_seconds)
                
                # Perform update
                logger.info("Starting scheduled update...")
                result = await self.fetch_and_store()
                
                if result['success']:
                    logger.info(f"Update completed: {result['observations']} observations")
                else:
                    logger.error(f"Update failed: {result.get('message', 'Unknown error')}")
                
                # Calculate next update time
                now = datetime.now()
                next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                wait_seconds = (next_hour - now).total_seconds()
                
                logger.info(f"Next update scheduled at {next_hour.strftime('%H:%M:%S')} ({wait_seconds/60:.1f} minutes)")
                
            except asyncio.CancelledError:
                logger.info("Update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in update loop: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting AMeDAS scheduler...")
        self.task = asyncio.create_task(self.update_loop())
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping AMeDAS scheduler...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler stopped")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            'running': self.running,
            'update_interval': self.update_interval,
            'update_interval_hours': self.update_interval / 3600,
            'json_path': self.json_path,
            'update_history': self.update_history[-10:]  # Last 10 updates
        }


# Global scheduler instance
_scheduler = None


def get_scheduler(update_interval: int = 3600, json_path: str = "amedas_data.json") -> AMeDASScheduler:
    """Get or create the scheduler singleton"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AMeDASScheduler(update_interval, json_path)
    return _scheduler


async def main():
    """Main function for standalone execution"""
    
    # Create scheduler (update every hour)
    scheduler = get_scheduler(update_interval=3600)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(scheduler.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start scheduler
    await scheduler.start()
    
    # Show status
    status = scheduler.get_status()
    logger.info(f"Scheduler running: {status['running']}")
    logger.info(f"Update interval: {status['update_interval_hours']:.1f} hours")
    logger.info(f"JSON export path: {status['json_path']}")
    logger.info(f"Recent updates: {len(status['update_history'])}")
    
    # Keep running until stopped
    try:
        while scheduler.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    # Stop scheduler
    await scheduler.stop()
    logger.info("Scheduler shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())


