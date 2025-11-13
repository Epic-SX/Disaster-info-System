/**
 * WebSocket configuration
 */

// Get the WebSocket URL based on the environment
export const getWebSocketUrl = (): string => {
  // Check if environment variable is set
  if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_WS_BASE_URL) {
    return `${process.env.NEXT_PUBLIC_WS_BASE_URL}/ws`;
  }
  
  // In development, use localhost
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // If running on localhost, use localhost for backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//localhost:8000/ws`;
    }
    
    // For external IPs, always use port 8000 for WebSocket
    return `${protocol}//${hostname}:8000/ws`;
  }
  
  // Fallback for server-side rendering
  return 'ws://localhost:8000/ws';
};

// Get alternative WebSocket URLs to try if the primary fails
export const getWebSocketFallbackUrls = (): string[] => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    const fallbacks = [];
    
    // If not localhost, try localhost as fallback
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      fallbacks.push(`${protocol}//localhost:8000/ws`);
    }
    
    // Try 127.0.0.1 as fallback
    if (hostname !== '127.0.0.1') {
      fallbacks.push(`${protocol}//127.0.0.1:8000/ws`);
    }
    
    // Try the same hostname without port (in case backend is on same port as frontend)
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      fallbacks.push(`${protocol}//${hostname}/ws`);
    }
    
    return fallbacks;
  }
  
  return [];
};

// Export the WebSocket URL (lazy evaluation to avoid SSR issues)
export const getWebSocketConfig = () => ({
  url: getWebSocketUrl(),
  fallbackUrls: getWebSocketFallbackUrls()
});

// For backward compatibility, but these should be used carefully
export const WEBSOCKET_URL = typeof window !== 'undefined' ? getWebSocketUrl() : 'ws://localhost:8000/ws';
export const WEBSOCKET_FALLBACK_URLS = typeof window !== 'undefined' ? getWebSocketFallbackUrls() : [];
