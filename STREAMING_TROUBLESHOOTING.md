# YouTube Live Streaming Troubleshooting Guide

## 503 Service Unavailable Error

### Problem
When trying to start YouTube Live streaming, you get a **503 Service Unavailable** error in the browser console.

### Root Cause
The backend requires **FFmpeg** and **Xvfb** to be installed on the server to handle video streaming. When these dependencies are missing, the backend returns a 503 error.

### Solution

#### Step 1: Install Required Dependencies

Run the following command on your server:

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg xvfb
```

#### Step 2: Verify Installation

Check that FFmpeg is properly installed:

```bash
ffmpeg -version
```

You should see FFmpeg version information displayed.

Check that Xvfb is installed:

```bash
xvfb-run --help
```

#### Step 3: Restart Backend Service

After installing the dependencies, restart the backend service:

```bash
pm2 restart disaster-backend
```

Or restart all services:

```bash
pm2 restart all
```

#### Step 4: Verify Backend Logs

Check the backend logs to ensure no errors:

```bash
pm2 logs disaster-backend --lines 50
```

#### Step 5: Test Streaming

1. Navigate to the YouTube Streaming Configuration page in your application
2. Enter your YouTube stream key
3. Click "Start Streaming"
4. The stream should start successfully

---

## 500 Internal Server Error

### Problem
When trying to start YouTube Live streaming, you get a **500 Internal Server Error** after successfully installing FFmpeg and Xvfb.

### Root Cause
The backend requires a web browser (Google Chrome or Chromium) to capture the dashboard for streaming. The error occurs when:
1. No browser is installed, or
2. The code cannot find the installed browser

### Solution

The system now automatically detects available browsers (google-chrome, chromium-browser, or chromium). If you see this error:

#### Check Browser Installation

```bash
which google-chrome chromium-browser chromium
```

If no browser is found, install Chromium:

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

Or install Google Chrome:

```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```

#### Restart Backend

After installing a browser, restart the backend:

```bash
pm2 restart disaster-backend
```

---

## Other Common Issues

### Issue: "Stream key is required" Error

**Solution:** Make sure you've entered your YouTube Live stream key from YouTube Studio.

### Issue: Stream Starts but Nothing Appears on YouTube

**Possible Causes:**
1. **Wait Time:** It can take 10-30 seconds for the stream to appear on YouTube
2. **Incorrect Stream Key:** Verify your stream key in YouTube Studio
3. **Network Issues:** Check server network connectivity
4. **Firewall Rules:** Ensure outbound connections to YouTube are allowed

**Steps to Fix:**
1. Wait at least 30 seconds
2. Check YouTube Studio → Live → Stream
3. Verify the stream key matches
4. Check backend logs: `pm2 logs disaster-backend`

### Issue: Stream Stops Unexpectedly

**Possible Causes:**
1. Server resource constraints (CPU/Memory)
2. Network interruption
3. FFmpeg process crashed

**Steps to Fix:**
1. Check server resources: `htop` or `top`
2. Check backend logs: `pm2 logs disaster-backend --err --lines 100`
3. Restart the backend: `pm2 restart disaster-backend`

### Issue: Poor Stream Quality

**Solution:** 
1. Check server bandwidth
2. Reduce stream resolution/bitrate in `backend/youtube_live_streaming.py`
3. Close unnecessary applications on the server

---

## Checking System Requirements

### Minimum Requirements for Streaming

- **CPU:** 2+ cores
- **RAM:** 2GB+ available
- **Bandwidth:** 5+ Mbps upload speed
- **Disk:** 1GB+ free space

### Check Current Resources

```bash
# Check CPU and memory usage
htop

# Check disk space
df -h

# Check network speed
speedtest-cli

# Check FFmpeg
ffmpeg -version

# Check Xvfb
xvfb-run --help
```

---

## Debug Commands

### View Real-time Backend Logs
```bash
pm2 logs disaster-backend
```

### View Last 100 Lines of Error Logs
```bash
pm2 logs disaster-backend --err --lines 100
```

### Check Streaming Status via API
```bash
curl http://49.212.176.130/api/streaming/status
```

### Manually Test FFmpeg
```bash
ffmpeg -version
```

### Check if Xvfb is Running
```bash
ps aux | grep Xvfb
```

---

## Additional Resources

- [FFmpeg Official Documentation](https://ffmpeg.org/documentation.html)
- [YouTube Live Streaming Documentation](https://support.google.com/youtube/answer/2853702)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)

---

## Contact & Support

If you continue to experience issues after following this guide:

1. Check backend logs for detailed error messages
2. Verify all dependencies are installed
3. Ensure server has sufficient resources
4. Check YouTube Studio for stream status

For implementation details, see:
- `YOUTUBE_LIVE_STREAMING_GUIDE.md`
- `QUICK_SETUP_STREAMING.md`

