# Quick Setup: YouTube Live Streaming

## ⚠️ Important: Install Dependencies First

The YouTube Live streaming feature requires FFmpeg and Xvfb. Please run:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg xvfb x11-xserver-utils xfonts-base
```

Or use the automated script:

```bash
cd /home/ubuntu/Disaster-info-System/backend
sudo ./install_streaming_dependencies.sh
```

## 🚀 Quick Start Guide

### Step 1: Get Your YouTube Stream Key

1. Go to https://studio.youtube.com
2. Click "Go Live" or "Create" → "Go Live"
3. Select "Stream" tab
4. Copy your **Stream Key**

**Your Stream Information:**
```
Stream Key: 4dzh-z5y1-69km-gw0u-0342
Stream URL: rtmp://a.rtmp.youtube.com/live2
```

### Step 2: Configure the Dashboard

1. Open: http://49.212.176.130/
2. Go to "YouTube Live" tab
3. Enter your stream key in the "配信設定" tab
4. Click "設定を保存" (Save Settings)

### Step 3: Start Streaming

1. Click "配信を開始" (Start Streaming)
2. Wait 10-30 seconds for the stream to start
3. Go to YouTube Studio to verify the stream is live
4. Your dashboard will now be broadcasting to YouTube Live!

## ✅ Verify Installation

Check if dependencies are installed:

```bash
which ffmpeg  # Should output: /usr/bin/ffmpeg
which Xvfb    # Should output: /usr/bin/Xvfb
```

Test the API:

```bash
curl http://49.212.176.130/api/streaming/status
```

## 📺 What Gets Streamed?

The system will stream your disaster dashboard at:
- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: 30 fps
- **Quality**: 4.5 Mbps video bitrate
- **Content**: Real-time disaster monitoring dashboard

## 🔧 Troubleshooting

### Error: "Missing required dependencies"

**Solution**: Install dependencies (see above)

### Error: "Failed to start streaming"

**Check**:
1. Is your stream key correct?
2. Are dependencies installed? Run: `which ffmpeg && which Xvfb`
3. Is the backend running? Run: `pm2 status`
4. Check backend logs: `pm2 logs disaster-backend`

### Stream not appearing on YouTube

**Wait**: It can take 10-30 seconds for the stream to appear on YouTube Studio

**Verify**:
1. Check YouTube Studio → Live → Stream
2. Look for "Stream Status" indicator
3. Ensure your stream key matches

## 📝 API Endpoints

```bash
# Start streaming
curl -X POST "http://49.212.176.130/api/streaming/start?stream_key=YOUR_KEY"

# Stop streaming  
curl -X POST "http://49.212.176.130/api/streaming/stop"

# Check status
curl -X GET "http://49.212.176.130/api/streaming/status"
```

## 📖 Full Documentation

For detailed documentation, see: `YOUTUBE_LIVE_STREAMING_GUIDE.md`

