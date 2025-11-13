/**
 * API Configuration for the Disaster Information System
 * Centralizes all API endpoints and provides utilities for making API calls
 */

// Base URLs from environment variables
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Improved build time detection
const isBuildTime = typeof window === 'undefined' && (
  process.env.NODE_ENV === 'production' || 
  process.env.NEXT_PHASE === 'phase-production-build' ||
  !process.env.NEXT_RUNTIME
);

// Check if we're in server environment
const isServer = typeof window === 'undefined';

// API Endpoints
export const API_ENDPOINTS = {
  // Health and basic endpoints
  health: '/api/health',
  test: '/api/test',
  
  // Chat endpoints
  chat: {
    messages: '/api/chat/messages',
    analytics: '/api/chat/analytics',
    response: '/api/chat/response',
    responses: '/api/chat/responses',
    test: '/api/chat/test',
  },
  
  // Disaster data endpoints
  disasters: {
    alerts: '/api/disasters',
    recent: '/api/disasters/alerts/recent',
    earthquakes: '/api/disasters/earthquakes/comprehensive',
    tsunami: '/api/disasters/tsunami',
    seismicHazard: '/api/disasters/seismic-hazard',
  },
  
  // Seismic data endpoints
  seismic: {
    stations: '/api/seismic/stations',
    waveform: '/api/seismic/waveform',
  },
  
  // P2P地震情報 API v2 endpoints
  p2p: {
    history: '/api/p2p/history',
    jmaQuakes: '/api/p2p/jma/quakes',
    jmaQuake: '/api/p2p/jma/quake',
    jmaTsunamis: '/api/p2p/jma/tsunamis',
    jmaTsunami: '/api/p2p/jma/tsunami',
    latestEarthquakes: '/api/p2p/earthquakes/latest',
    latestTsunamis: '/api/p2p/tsunamis/latest',
    latestEEW: '/api/p2p/eew/latest',
    status: '/api/p2p/status',
  },
  
  // Earthquake specific endpoints
  earthquake: {
    data: '/api/earthquakes',
    recent: '/api/earthquake/recent',
  },
  
  // Tsunami endpoints
  tsunami: {
    alerts: '/api/tsunami/alerts',
  },
  
  // Weather endpoints
  weather: {
    wind: '/api/weather/wind',
  },
  
  // YouTube endpoints
  youtube: {
    search: '/api/youtube/search',
    videoDetails: '/api/youtube/video',
    liveStreams: '/api/youtube/live-streams',
    channels: '/api/youtube/channels',
    location: '/api/youtube/location',
    trending: '/api/youtube/trending',
    advanced: '/api/youtube/search/advanced',
  },
  
  // News endpoints
  news: '/api/news',
  
  // Debug endpoints
  debug: {
    messages: '/api/debug/messages',
  },
} as const;

// WebSocket endpoints
export const WS_ENDPOINTS = {
  main: '/ws',
} as const;

/**
 * Utility function to create full API URL
 */
export function createApiUrl(endpoint: string): string {
  return `${API_BASE_URL}${endpoint}`;
}

/**
 * Create WebSocket connection
 */
export function createWebSocket(endpoint: string): WebSocket | null {
  // Don't create WebSocket during SSR or build time
  if (isServer || isBuildTime) {
    console.log('Skipping WebSocket creation during SSR/build time');
    return null;
  }
  
  try {
    // Use the same host as API_BASE_URL but with ws protocol
    const apiUrl = new URL(API_BASE_URL);
    const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBaseUrl = process.env.NEXT_PUBLIC_WS_BASE_URL || `${protocol}//${apiUrl.host}`;
    const fullWsUrl = `${wsBaseUrl}${endpoint}`;
    
    console.log('Attempting WebSocket connection to:', fullWsUrl);
    
    // Create WebSocket with longer timeout and better error handling
    const ws = new WebSocket(fullWsUrl);
    
    // Set a connection timeout
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        console.log('WebSocket connection timeout, closing...');
        ws.close();
      }
    }, 10000); // 10 second timeout
    
    // Clear timeout when connection opens
    ws.addEventListener('open', () => {
      clearTimeout(connectionTimeout);
      console.log('WebSocket connection established successfully');
    });
    
    // Clear timeout when connection fails
    ws.addEventListener('error', () => {
      clearTimeout(connectionTimeout);
    });
    
    return ws;
  } catch (error) {
    console.error('Failed to create WebSocket:', error);
    return null;
  }
}

/**
 * Generic API fetch utility with error handling
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Skip API calls during build time or if no fetch available
  if (isBuildTime || typeof fetch === 'undefined') {
    console.log('Skipping API call during build time:', endpoint);
    return {} as T;
  }

  const url = createApiUrl(endpoint);
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };
  
  const requestOptions = { ...defaultOptions, ...options };
  
  try {
    const response = await fetch(url, requestOptions);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
    
    // Check if response has content
    const contentLength = response.headers.get('content-length');
    if (contentLength === '0') {
      return {} as T;
    }
    
    const contentType = response.headers.get('Content-Type');
    if (contentType && contentType.includes('application/json')) {
      const text = await response.text();
      if (!text || text.trim() === '') {
        return {} as T;
      }
      
      try {
        return JSON.parse(text);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Response text:', text);
        return {} as T;
      }
    }
    
    return await response.text() as T;
  } catch (error) {
    console.error(`API request to ${url} failed:`, error);
    // Return empty object instead of throwing during build
    if (isBuildTime || isServer) {
      return {} as T;
    }
    throw error;
  }
}

/**
 * Typed API client for common operations
 */
export const apiClient = {
  // GET request
  get: <T = any>(endpoint: string) => 
    apiRequest<T>(endpoint, { method: 'GET' }),
  
  // POST request
  post: <T = any>(endpoint: string, data?: any) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  // PUT request
  put: <T = any>(endpoint: string, data?: any) =>
    apiRequest<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  // DELETE request
  delete: <T = any>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: 'DELETE' }),
};
