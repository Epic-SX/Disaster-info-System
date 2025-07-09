# Disaster Information System - Backend

This is the Python backend for the Disaster Information System, providing real-time disaster monitoring, YouTube Live Chat integration, and social media automation.

## Features

- 🌊 **Real-time Disaster Monitoring**: Integration with earthquake, tsunami, and weather APIs
  - **P2P地震情報 API**: Real-time earthquake data from community sources
  - **J-SHIS Map API**: Seismic hazard information and active fault data
  - **IIJ Engineering WebSocket**: Real-time earthquake flash alerts
  - **USGS Earthquake API**: Global earthquake monitoring
- 💬 **YouTube Live Chat Integration**: Real-time chat analysis and auto-responses
- 🔍 **YouTube Search Integration**: Search disaster-related videos using SerpApi
  - Search for disaster-related content
  - Find live disaster streams
  - Track trending disaster topics
- 🤖 **AI-Powered Content Generation**: Automated social media posts using OpenAI
- 📊 **Analytics Dashboard**: Chat sentiment analysis and engagement metrics
- 🔄 **WebSocket Support**: Real-time updates to frontend applications
- 📱 **Social Media Automation**: Automated posting to Twitter, Facebook, Instagram

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Required API keys (see Configuration section)

## Quick Start

1. **Clone and navigate to the backend directory**:
   ```bash
   cd disaster-info-system/backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Start the backend**:
   ```bash
   python start_backend.py
   ```

The backend will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

## Configuration

### Required API Keys

Create a `.env` file based on `.env.example` and add your API keys:

```env
# Essential for AI features
OPENAI_API_KEY=your_openai_api_key_here

# Required for YouTube Live Chat
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_CHANNEL_ID=your_youtube_channel_id_here

# SerpApi for YouTube Search (NEW!)
SERPAPI_API_KEY=your_serpapi_api_key_here

# Additional Disaster APIs (NEW!)
P2P_EARTHQUAKE_API=https://api.p2pquake.net/v2
J_SHIS_API_BASE=https://www.j-shis.bosai.go.jp/map
IIJ_EARTHQUAKE_WEBSOCKET=wss://ws-api.iij.jp/v1/earthquake

# Social Media APIs (optional but recommended)
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here

FACEBOOK_ACCESS_TOKEN=your_facebook_access_token_here
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
```

### Getting API Keys

#### OpenAI API Key
1. Visit [OpenAI API](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Create a new API key
4. Add billing information (required for API usage)

#### YouTube API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the YouTube Data API v3
4. Create credentials (API Key)
5. Get your channel ID from your YouTube channel URL

#### SerpApi Key (NEW!)
1. Visit [SerpApi](https://serpapi.com/manage-api-key)
2. Sign up for an account
3. Get your API key from the dashboard
4. Used for YouTube video search functionality

#### Social Media APIs
- **Twitter**: Apply for developer access at [Twitter Developer Portal](https://developer.twitter.com/)
- **Facebook/Instagram**: Use [Facebook Developer Console](https://developers.facebook.com/)

## API Endpoints

### Health & Status
- `GET /` - API information and status
- `GET /api/health` - Health check

### Disaster Data
- `GET /api/disasters` - Current disaster alerts
- `GET /api/earthquakes` - Recent earthquake data (legacy)
- `GET /api/disasters/earthquakes/comprehensive` - **NEW!** Comprehensive earthquake data from multiple sources
- `GET /api/disasters/tsunami` - **NEW!** Current tsunami alerts
- `GET /api/disasters/alerts/recent` - **NEW!** Recent disaster alerts from all sources
- `GET /api/disasters/seismic-hazard` - **NEW!** Seismic hazard info for coordinates
- `GET /api/news` - Disaster-related news articles

### YouTube Integration
- `GET /api/chat/messages` - Recent chat messages
- `GET /api/chat/analytics` - Chat analytics and metrics
- `POST /api/chat/response` - Send chat response
- `GET /api/chat/responses` - Get auto-response configurations
- `GET /api/youtube/search` - **NEW!** Search disaster-related YouTube videos
- `GET /api/youtube/live-streams` - **NEW!** Find live disaster streams
- `GET /api/youtube/trending` - **NEW!** Get trending disaster topics

### WebSocket
- `WS /ws` - Real-time updates for chat and disaster alerts

## Architecture

```
backend/
├── main.py                      # FastAPI application
├── youtube_chat_service.py      # YouTube Live Chat integration
├── youtube_search_service.py    # NEW! YouTube search via SerpApi
├── disaster_api_service.py      # NEW! Comprehensive disaster APIs
├── start_backend.py             # Startup script
├── requirements.txt             # Python dependencies
├── .env.example                # Environment variables template
├── .env                        # Your environment variables (create this)
├── disaster_chat.db            # SQLite database (auto-created)
└── disaster_data.db            # NEW! Disaster data database (auto-created)
```

## Data Sources

### Earthquake Information
- **P2P地震情報**: Community-sourced real-time earthquake data
- **USGS**: Global earthquake monitoring
- **IIJ Engineering**: Real-time earthquake flash alerts via WebSocket

### Tsunami Alerts
- **P2P地震情報**: Community tsunami alert system
- **JMA (Japan Meteorological Agency)**: Official tsunami warnings

### YouTube Content
- **SerpApi**: YouTube video search for disaster-related content
- **YouTube Data API**: Live chat integration and channel management

### Seismic Hazard
- **J-SHIS**: Japan Seismic Hazard Information Station for hazard maps

## Services

### YouTube Chat Analyzer
- Monitors live chat in real-time using `pytchat`
- Performs sentiment analysis on messages
- Categorizes messages (disaster-related, product inquiries, general)
- Generates AI-powered auto-responses
- Stores chat history and analytics

### YouTube Search Service (NEW!)
- Search for disaster-related videos using SerpApi
- Find live disaster streams
- Track trending disaster topics
- Automated content discovery for emergency response

### Disaster API Service (NEW!)
- Comprehensive earthquake monitoring from multiple sources
- Real-time tsunami alert aggregation
- WebSocket-based real-time earthquake notifications
- Seismic hazard mapping integration
- Duplicate detection and data normalization

### Social Media Automation
- Scheduled posting to multiple platforms
- AI-generated content based on disaster alerts
- Product promotion automation
- Engagement tracking and analytics

## Database Schema

The backend uses SQLite with the following main tables:

### Chat Database (`disaster_chat.db`)
- `chat_messages`: YouTube chat message history
- `auto_responses`: Configured automatic responses

### Disaster Database (`disaster_data.db`) - NEW!
- `earthquakes`: Comprehensive earthquake data from all sources
- `disaster_alerts`: Generated disaster alerts with metadata

## Development

### Running in Development Mode

```bash
# Start with auto-reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script
python start_backend.py
```

### Testing the New APIs

```bash
# Test YouTube search
curl "http://localhost:8000/api/youtube/search?query=地震&limit=5"

# Test comprehensive earthquake data
curl "http://localhost:8000/api/disasters/earthquakes/comprehensive"

# Test tsunami alerts
curl "http://localhost:8000/api/disasters/tsunami"

# Test recent disaster alerts
curl "http://localhost:8000/api/disasters/alerts/recent?hours=12"
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=.
```

## Real-Time Features

### WebSocket Monitoring
The system provides real-time updates via WebSocket connections:
- Live earthquake alerts from IIJ Engineering
- Chat message processing
- Disaster alert notifications

### Background Tasks
- Continuous earthquake monitoring
- Chat analysis and auto-response
- Data aggregation from multiple sources
- Alert generation and distribution

## Monitoring and Logs

The backend provides comprehensive logging:

```bash
# View logs in real-time
tail -f logs/disaster_backend.log

# Check service status
curl http://localhost:8000/api/health
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Ensure SQLite permissions are correct
2. **YouTube API quota exceeded**: Monitor your API usage in Google Cloud Console
3. **OpenAI API errors**: Check your API key and billing status
4. **WebSocket connection issues**: Verify CORS settings for your frontend

### Debug Mode

Enable debug mode in `.env`:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

## Production Deployment

### Using Docker (Recommended)

```dockerfile
# Create Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "start_backend.py"]
```

### Using Systemd (Linux)

Create a service file at `/etc/systemd/system/disaster-backend.service`:

```ini
[Unit]
Description=Disaster Information System Backend
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/disaster-info-system/backend
ExecStart=/usr/bin/python3 start_backend.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables for Production

```env
DEBUG=False
LOG_LEVEL=WARNING
HOST=0.0.0.0
PORT=8000
```

## Security Considerations

- Store API keys securely (never commit to version control)
- Use HTTPS in production
- Implement rate limiting for public endpoints
- Regular security updates for dependencies
- Monitor API usage and costs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE for details.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review API documentation at `/docs`
- Check logs for error details
- Ensure all required API keys are configured

## Changelog

### Version 1.0.0
- Initial release with YouTube Live Chat integration
- Basic disaster monitoring APIs
- Social media automation framework
- WebSocket support for real-time updates 