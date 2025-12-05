#!/bin/bash
# Quick setup script for YouTube API Key

echo "=========================================="
echo "  YouTube API Key Setup"
echo "=========================================="
echo ""

# Check if API key is provided as argument
if [ -z "$1" ]; then
    echo "Usage: ./setup_youtube_api_key.sh YOUR_API_KEY"
    echo ""
    echo "Example:"
    echo "  ./setup_youtube_api_key.sh AIzaSyABCDEF1234567890"
    echo ""
    echo "To get your API key:"
    echo "  1. Go to: https://console.cloud.google.com/"
    echo "  2. Enable YouTube Data API v3"
    echo "  3. Create an API Key"
    echo ""
    echo "See GET_YOUTUBE_API_KEY.md for detailed instructions"
    exit 1
fi

API_KEY="$1"

echo "Setting up YouTube API Key..."
echo ""

# Create or update .env file
ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    echo "✓ Found existing .env file"
    # Check if YOUTUBE_API_KEY already exists
    if grep -q "YOUTUBE_API_KEY=" "$ENV_FILE"; then
        echo "✓ Updating existing YOUTUBE_API_KEY"
        # Use different delimiter for sed to avoid issues with special chars
        sed -i "s|YOUTUBE_API_KEY=.*|YOUTUBE_API_KEY=$API_KEY|" "$ENV_FILE"
    else
        echo "✓ Adding YOUTUBE_API_KEY to .env"
        echo "YOUTUBE_API_KEY=$API_KEY" >> "$ENV_FILE"
    fi
else
    echo "✓ Creating new .env file"
    cat > "$ENV_FILE" << EOF
# YouTube Data API v3 Key
YOUTUBE_API_KEY=$API_KEY

# Other API Keys (add as needed)
# OPENAI_API_KEY=your_openai_key_here
# YOUTUBE_CHANNEL_ID=your_channel_id_here
EOF
fi

echo ""
echo "✅ API Key configured successfully!"
echo ""

# Export for current session
export YOUTUBE_API_KEY="$API_KEY"

# Test the API key
echo "Testing API key..."
echo ""

# Use curl to test
TEST_URL="https://www.googleapis.com/youtube/v3/search?part=snippet&q=test&maxResults=1&key=$API_KEY"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TEST_URL")

if [ "$RESPONSE" = "200" ]; then
    echo "✅ API Key is valid and working!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart the backend server"
    echo "     cd /home/ubuntu/Disaster-info-System/backend"
    echo "     pkill -f 'python.*main.py'"
    echo "     python main.py &"
    echo ""
    echo "  2. Test the YouTube search"
    echo "     curl 'http://localhost:8000/api/youtube/search?query=test&limit=1'"
    echo ""
elif [ "$RESPONSE" = "403" ]; then
    echo "⚠️  API Key configured but getting 403 Forbidden"
    echo ""
    echo "Possible issues:"
    echo "  - API key may need time to activate (wait 1-2 minutes)"
    echo "  - YouTube Data API v3 not enabled"
    echo "  - API key has restrictions preventing this request"
    echo "  - Quota exceeded"
    echo ""
    echo "Go to: https://console.cloud.google.com/"
    echo "  → APIs & Services → Library"
    echo "  → Enable 'YouTube Data API v3'"
    echo ""
elif [ "$RESPONSE" = "400" ]; then
    echo "❌ Invalid API Key"
    echo ""
    echo "Please check:"
    echo "  - API key is copied correctly"
    echo "  - No extra spaces or characters"
    echo "  - Using a YouTube Data API v3 key"
    echo ""
else
    echo "⚠️  Got HTTP $RESPONSE"
    echo ""
    echo "The API key has been saved, but there might be an issue."
    echo "Try restarting the backend and test again."
    echo ""
fi

echo "Configuration saved to: $ENV_FILE"
echo ""

