#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live Streaming Service
Manages streaming the disaster dashboard to YouTube Live using FFmpeg
"""

import os
import subprocess
import logging
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class YouTubeLiveStreamer:
    """Manages YouTube Live streaming with FFmpeg"""
    
    def __init__(self, stream_key: str, stream_url: str = "rtmp://a.rtmp.youtube.com/live2"):
        """
        Initialize YouTube Live Streamer
        
        Args:
            stream_key: YouTube Live stream key
            stream_url: RTMP server URL (default is YouTube's server)
        """
        self.stream_key = stream_key
        self.stream_url = stream_url
        self.process = None
        self.is_streaming = False
        self.dashboard_url = os.getenv('DASHBOARD_URL', 'http://49.212.176.130/')
        
        # Streaming parameters
        self.resolution = "1920x1080"  # Full HD
        self.framerate = 30
        self.video_bitrate = "4500k"
        self.audio_bitrate = "128k"
        self.preset = "veryfast"  # Balance between quality and CPU usage
        
        logger.info("YouTube Live Streamer initialized")
    
    def start_streaming(self, dashboard_url: Optional[str] = None) -> bool:
        """
        Start streaming the dashboard to YouTube Live
        
        Args:
            dashboard_url: URL of the dashboard to stream (overrides default)
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        if self.is_streaming:
            logger.warning("Streaming is already active")
            return False
        
        url = dashboard_url or self.dashboard_url
        rtmp_url = f"{self.stream_url}/{self.stream_key}"
        
        # FFmpeg command to capture screen and stream to YouTube
        # Using virtual display (Xvfb) + browser capture approach
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'x11grab',                    # Capture from X11 display
            '-r', str(self.framerate),           # Frame rate
            '-s', self.resolution,               # Resolution
            '-i', ':99',                         # Virtual display :99 (Xvfb)
            '-f', 'pulse',                       # Audio input (pulse audio)
            '-i', 'default',                     # Default audio device
            '-vcodec', 'libx264',                # H.264 video codec
            '-preset', self.preset,              # Encoding preset
            '-b:v', self.video_bitrate,          # Video bitrate
            '-maxrate', self.video_bitrate,      # Max bitrate
            '-bufsize', '9000k',                 # Buffer size
            '-pix_fmt', 'yuv420p',               # Pixel format
            '-g', str(self.framerate * 2),       # GOP size (2 seconds)
            '-acodec', 'aac',                    # AAC audio codec
            '-b:a', self.audio_bitrate,          # Audio bitrate
            '-ar', '44100',                      # Audio sample rate
            '-f', 'flv',                         # Output format
            rtmp_url                             # RTMP destination
        ]
        
        try:
            logger.info(f"Starting YouTube Live stream to: {self.stream_url}")
            logger.info(f"Dashboard URL: {url}")
            
            # Start FFmpeg process
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.is_streaming = True
            logger.info("YouTube Live streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {str(e)}")
            self.is_streaming = False
            return False
    
    def start_streaming_with_browser(self, dashboard_url: Optional[str] = None) -> bool:
        """
        Start streaming using browser-based capture (Chrome headless)
        This method is more reliable for web dashboards
        
        Args:
            dashboard_url: URL of the dashboard to stream
        
        Returns:
            True if streaming started successfully
        """
        if self.is_streaming:
            logger.warning("Streaming is already active")
            return False
        
        url = dashboard_url or self.dashboard_url
        rtmp_url = f"{self.stream_url}/{self.stream_key}"
        
        # Start Xvfb (virtual display) if not running
        xvfb_cmd = ['Xvfb', ':99', '-screen', '0', '1920x1080x24', '-ac', '+extension', 'GLX']
        
        try:
            # Start Xvfb
            xvfb_process = subprocess.Popen(xvfb_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Started Xvfb virtual display")
            
            # Wait for Xvfb to initialize
            import time
            time.sleep(2)
            
            # Open browser in virtual display
            browser_cmd = [
                'google-chrome',
                '--display=:99',
                '--kiosk',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--autoplay-policy=no-user-gesture-required',
                url
            ]
            
            browser_process = subprocess.Popen(browser_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Opened browser at {url}")
            
            # Wait for browser to load
            time.sleep(5)
            
            # Now start FFmpeg to capture and stream
            return self.start_streaming(dashboard_url)
            
        except Exception as e:
            logger.error(f"Failed to start browser streaming: {str(e)}")
            return False
    
    def stop_streaming(self) -> bool:
        """
        Stop the streaming
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_streaming or not self.process:
            logger.warning("No active stream to stop")
            return False
        
        try:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.is_streaming = False
            logger.info("YouTube Live streaming stopped")
            return True
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg did not terminate gracefully, forcing kill")
            self.process.kill()
            self.is_streaming = False
            return True
        except Exception as e:
            logger.error(f"Error stopping stream: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        return {
            "is_streaming": self.is_streaming,
            "dashboard_url": self.dashboard_url,
            "stream_url": self.stream_url,
            "resolution": self.resolution,
            "framerate": self.framerate,
            "video_bitrate": self.video_bitrate,
            "process_alive": self.process.poll() is None if self.process else False
        }


class OBSStreamingConfig:
    """Generate OBS Studio configuration for streaming the dashboard"""
    
    @staticmethod
    def generate_obs_config(stream_key: str, dashboard_url: str = "http://49.212.176.130/") -> Dict[str, Any]:
        """
        Generate OBS configuration JSON
        
        Args:
            stream_key: YouTube stream key
            dashboard_url: Dashboard URL to capture
        
        Returns:
            OBS configuration dictionary
        """
        config = {
            "streaming": {
                "service": "YouTube / YouTube Gaming",
                "server": "rtmp://a.rtmp.youtube.com/live2",
                "key": stream_key
            },
            "video": {
                "base_resolution": "1920x1080",
                "output_resolution": "1920x1080",
                "fps": 30
            },
            "output": {
                "mode": "Advanced",
                "encoder": "x264",
                "rate_control": "CBR",
                "bitrate": 4500,
                "keyframe_interval": 2,
                "preset": "veryfast",
                "profile": "main",
                "tune": "zerolatency"
            },
            "audio": {
                "sample_rate": 44100,
                "channels": "Stereo",
                "bitrate": 128
            },
            "sources": [
                {
                    "name": "Disaster Dashboard",
                    "type": "browser_source",
                    "settings": {
                        "url": dashboard_url,
                        "width": 1920,
                        "height": 1080,
                        "fps": 30,
                        "css": "body { margin: 0px auto; overflow: hidden; }"
                    }
                }
            ],
            "scenes": [
                {
                    "name": "Main Scene",
                    "sources": ["Disaster Dashboard"]
                }
            ]
        }
        return config
    
    @staticmethod
    def save_obs_config(stream_key: str, output_file: str = "obs_config.json", 
                       dashboard_url: str = "http://49.212.176.130/") -> str:
        """
        Save OBS configuration to file
        
        Args:
            stream_key: YouTube stream key
            output_file: Output configuration file path
            dashboard_url: Dashboard URL
        
        Returns:
            Path to saved configuration file
        """
        config = OBSStreamingConfig.generate_obs_config(stream_key, dashboard_url)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OBS configuration saved to {output_file}")
        return output_file


class SimpleHTTPStreamer:
    """Simple HTTP-based streaming alternative using simpler tools"""
    
    def __init__(self, stream_key: str):
        self.stream_key = stream_key
        self.process = None
        
    def start_stream_from_url(self, url: str = "http://49.212.176.130/") -> bool:
        """
        Start streaming by capturing browser window
        Uses simpler approach with video4linux loopback
        
        Args:
            url: Dashboard URL to stream
        
        Returns:
            True if started successfully
        """
        rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{self.stream_key}"
        
        # Command to use chromium with screen capture via v4l2loopback
        cmd = [
            'ffmpeg',
            '-re',  # Read input at native frame rate
            '-f', 'lavfi',
            '-i', f'movie=filename={url}:loop=0, setpts=N/(30*TB)',  # Loop video
            '-vcodec', 'libx264',
            '-preset', 'veryfast',
            '-b:v', '4500k',
            '-maxrate', '4500k',
            '-bufsize', '9000k',
            '-pix_fmt', 'yuv420p',
            '-g', '60',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-f', 'flv',
            rtmp_url
        ]
        
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("Started simple HTTP streaming")
            return True
        except Exception as e:
            logger.error(f"Failed to start simple streaming: {str(e)}")
            return False


# Singleton instance
_streamer = None

def get_streamer(stream_key: str) -> YouTubeLiveStreamer:
    """Get or create the streamer singleton"""
    global _streamer
    if _streamer is None:
        _streamer = YouTubeLiveStreamer(stream_key)
    return _streamer


if __name__ == "__main__":
    # Test/demo mode
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    stream_key = os.getenv('YOUTUBE_STREAM_KEY', 'your-stream-key-here')
    
    streamer = YouTubeLiveStreamer(stream_key)
    
    print("YouTube Live Streaming Configuration")
    print("=" * 50)
    print(f"Dashboard URL: {streamer.dashboard_url}")
    print(f"Stream Server: {streamer.stream_url}")
    print(f"Resolution: {streamer.resolution}")
    print(f"Frame Rate: {streamer.framerate} fps")
    print(f"Video Bitrate: {streamer.video_bitrate}")
    print("=" * 50)
    print("\nTo start streaming, ensure you have:")
    print("1. FFmpeg installed")
    print("2. Xvfb for virtual display (optional)")
    print("3. Valid YouTube stream key")
    print("4. Dashboard is accessible at the URL")
    print("\nGenerate OBS config with:")
    obs_config_file = OBSStreamingConfig.save_obs_config(stream_key)
    print(f"OBS config saved to: {obs_config_file}")

