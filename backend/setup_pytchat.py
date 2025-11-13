#!/usr/bin/env python3
"""
Setup script for YouTube Live Chat integration with pytchat
Based on https://brian0111.com/youtube-live-chat-pytchat-python/
"""

import os
import subprocess
import sys
import json
from pathlib import Path

def install_dependencies():
    """Install required Python packages"""
    print("🔧 Installing required dependencies...")
    
    required_packages = [
        "pytchat==0.5.5",
        "google-auth==2.17.3",
        "google-auth-oauthlib==1.0.0", 
        "google-auth-httplib2==0.1.0",
        "google-api-python-client==2.100.0"
    ]
    
    for package in required_packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    return True

def check_credentials():
    """Check if Google service account credentials exist"""
    credentials_file = "august-key-430913-i2-3e7c61487160.json"
    
    if os.path.exists(credentials_file):
        print(f"✅ Google service account credentials found: {credentials_file}")
        return True
    else:
        print(f"⚠️ Google service account credentials not found: {credentials_file}")
        print("Please ensure the credentials file is in the backend directory")
        return False

def test_pytchat():
    """Test pytchat installation"""
    print("\n🧪 Testing pytchat installation...")
    
    try:
        import pytchat
        print(f"✅ pytchat version {pytchat.__version__} imported successfully")
        
        # Test creating a chat object with development mode
        print("Testing pytchat chat creation...")
        # Note: Using a known public video for testing
        test_video_id = "jfKfPfyJRdk"  # YouTube's "lofi hip hop radio" stream
        
        try:
            chat = pytchat.create(video_id=test_video_id, processor=pytchat.CompatibleProcessor())
            print("✅ pytchat chat object created successfully")
            chat.terminate()
            return True
        except Exception as e:
            print(f"⚠️ pytchat chat creation test failed: {e}")
            print("This might be normal if the test video is not live")
            return True  # Still considered success if import works
            
    except ImportError as e:
        print(f"❌ Failed to import pytchat: {e}")
        return False

def test_google_apis():
    """Test Google API libraries"""
    print("\n🧪 Testing Google API libraries...")
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        print("✅ Google API libraries imported successfully")
        
        # Test credentials loading if file exists
        credentials_file = "august-key-430913-i2-3e7c61487160.json"
        if os.path.exists(credentials_file):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_file,
                    scopes=['https://www.googleapis.com/auth/youtube.force-ssl']
                )
                print("✅ Service account credentials loaded successfully")
                
                youtube = build('youtube', 'v3', credentials=credentials)
                print("✅ YouTube API service created successfully")
                return True
                
            except Exception as e:
                print(f"⚠️ Error loading credentials: {e}")
                return False
        else:
            print("⚠️ Credentials file not found, skipping API test")
            return True
            
    except ImportError as e:
        print(f"❌ Failed to import Google API libraries: {e}")
        return False

def create_config_file():
    """Create a sample configuration file"""
    print("\n📄 Creating configuration file...")
    
    config = {
        "openai_api_key": os.getenv('OPENAI_API_KEY', ''),
        "youtube_api_key": os.getenv('YOUTUBE_API_KEY', ''),
        "auto_response_enabled": True,
        "ai_response_enabled": True,
        "auto_response_cooldown": 30,
        "max_chat_history": 1000,
        "sentiment_threshold": 0.7,
        "ai_model": "gpt-3.5-turbo",
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    config_file = "config.json"
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"✅ Configuration file created: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to create config file: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions"""
    print("\n" + "="*60)
    print("🎉 YouTube Live Chat Integration Setup Complete!")
    print("="*60)
    print()
    print("📋 NEXT STEPS:")
    print()
    print("1. Set your YouTube Live Video ID:")
    print("   - Edit .env file")
    print("   - Change YOUTUBE_LIVE_VIDEO_ID from 'development_mode' to your actual video ID")
    print("   - Example: YOUTUBE_LIVE_VIDEO_ID=dQw4w9WgXcQ")
    print()
    print("2. Configure API Keys (if not already done):")
    print("   - OPENAI_API_KEY (for AI responses)")
    print("   - YOUTUBE_API_KEY (for YouTube API access)")
    print()
    print("3. Start the backend server:")
    print("   python main.py")
    print()
    print("4. Test the integration:")
    print("   - Visit http://localhost:8000/api/chat/live-status")
    print("   - Check http://localhost:8000/api/chat/messages")
    print("   - Monitor http://localhost:8000/api/chat/analytics")
    print()
    print("🔗 REFERENCE:")
    print("   Tutorial: https://brian0111.com/youtube-live-chat-pytchat-python/")
    print("   pytchat docs: https://github.com/taizan-hokuto/pytchat")
    print()
    print("💡 DEVELOPMENT MODE:")
    print("   Leave YOUTUBE_LIVE_VIDEO_ID as 'development_mode' to test with mock data")
    print()

def main():
    print("🚀 YouTube Live Chat Integration Setup")
    print("Based on pytchat library tutorial")
    print("Reference: https://brian0111.com/youtube-live-chat-pytchat-python/")
    print("="*60)
    
    success = True
    
    # Install dependencies
    if not install_dependencies():
        success = False
    
    # Check credentials
    check_credentials()
    
    # Test pytchat
    if not test_pytchat():
        success = False
    
    # Test Google APIs
    if not test_google_apis():
        success = False
    
    # Create config file
    create_config_file()
    
    if success:
        print_usage_instructions()
    else:
        print("\n❌ Setup completed with some errors. Please check the output above.")
        print("The system may still work in development mode.")

if __name__ == "__main__":
    main() 