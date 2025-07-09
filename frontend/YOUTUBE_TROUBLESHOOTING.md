# YouTube Player Troubleshooting Guide

## Issue: YouTube IFrame API Connection Timeout

### Problem
The error `GET https://www.youtube.com/iframe_api net::ERR_CONNECTION_TIMED_OUT` indicates that your browser cannot connect to YouTube's servers to load the IFrame API.

### Solutions Implemented

#### 1. Hybrid Player System
The system now automatically detects YouTube connectivity and falls back to alternatives:

- **Primary**: YouTube IFrame API (full functionality)
- **Fallback**: YouTube embed iframe (basic functionality)
- **Ultimate fallback**: Direct YouTube links

#### 2. Error Handling & Recovery
- Automatic timeout detection (10 seconds)
- Retry mechanisms
- User-friendly error messages
- Manual retry buttons

#### 3. Alternative Domains
- Uses `youtube-nocookie.com` for better privacy and potentially better connectivity
- Falls back to standard `youtube.com` if needed

### Manual Solutions

#### Network-Based Solutions
1. **Check Internet Connection**: Ensure stable internet connectivity
2. **Disable VPN**: Some VPNs may block YouTube API calls
3. **Check Firewall**: Ensure YouTube domains are not blocked
4. **DNS Issues**: Try using public DNS (8.8.8.8, 1.1.1.1)

#### Browser-Based Solutions
1. **Clear Browser Cache**: Clear cache and cookies
2. **Disable Extensions**: Temporarily disable ad blockers or privacy extensions
3. **Try Incognito Mode**: Test in private/incognito browser window
4. **Update Browser**: Ensure you're using the latest browser version

#### Corporate/Regional Restrictions
If YouTube is blocked in your region or network:
1. The embed fallback will automatically activate
2. Videos will still be playable but with limited functionality
3. Direct YouTube links are provided as last resort

### Component Usage

#### Use Hybrid Player (Recommended)
```tsx
import { YouTubePlayerHybrid } from "@/components/YouTubePlayer";

<YouTubePlayerHybrid
  videoId="your-video-id"
  title="Your Title"
  autoplay={true}
  muted={true}
/>
```

#### Use Embed Player (For Restricted Networks)
```tsx
import { YouTubeEmbedPlayer } from "@/components/YouTubePlayer";

<YouTubeEmbedPlayer
  videoId="your-video-id"
  title="Your Title"
  autoplay={true}
  muted={true}
/>
```

#### Force API Player (If You Know It Works)
```tsx
import { YouTubePlayer } from "@/components/YouTubePlayer";

<YouTubePlayer
  videoId="your-video-id"
  title="Your Title"
  autoplay={true}
  muted={true}
/>
```

### Configuration

Edit `lib/youtube-config.ts` to customize behavior:

```ts
export const YOUTUBE_CONFIG = {
  // Enable/disable fallback mechanisms
  enableAPIFallback: true,
  enableEmbedFallback: true,
  useHybridByDefault: true,
  
  // Adjust timeout settings
  apiLoadTimeout: 10000, // 10 seconds
  connectivityTestTimeout: 5000, // 5 seconds
};
```

### Testing Connectivity

You can test YouTube connectivity programmatically:

```ts
import { testYouTubeConnectivity, getBestPlayerMode } from "@/lib/youtube-config";

// Test connectivity
const isAccessible = await testYouTubeConnectivity();

// Get recommended player mode
const mode = await getBestPlayerMode();
```

### Status Indicators

The hybrid player shows status badges:
- **🔴 LIVE**: For live streams
- **🔵 埋め込みモード**: When using embed fallback
- **🔄 再試行**: Retry button for failed connections

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `YouTube API接続エラー` | Cannot load IFrame API | Uses embed fallback automatically |
| `動画を読み込めません` | Embed also failed | Network/regional restrictions |
| `YouTube API読み込み中...` | Loading state | Wait or check network |

### Development Notes

For development, you can force specific modes by setting environment variables:

```env
NEXT_PUBLIC_YOUTUBE_FORCE_MODE=embed  # Force embed mode
NEXT_PUBLIC_YOUTUBE_FORCE_MODE=api    # Force API mode
NEXT_PUBLIC_YOUTUBE_FORCE_MODE=hybrid # Use hybrid (default)
```

### Support

If all fallbacks fail, the system provides:
1. Clear error messages
2. Retry mechanisms
3. Direct YouTube links
4. Alternative video sources (if configured)

The hybrid system ensures your disaster monitoring system remains functional even in restricted network environments. 