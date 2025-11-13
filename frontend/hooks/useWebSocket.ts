import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp: string;
}

interface UseWebSocketOptions {
  url: string;
  fallbackUrls?: string[];
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export const useWebSocket = ({
  url,
  fallbackUrls = [],
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnectInterval = 5000,
  maxReconnectAttempts = 5
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUrl, setCurrentUrl] = useState(url);
  const [isDisabled, setIsDisabled] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const urlIndex = useRef(0);
  const consecutiveFailures = useRef(0);

  const connect = () => {
    try {
      // Skip WebSocket connection during build time or server-side rendering
      if (typeof window === 'undefined') {
        console.log('Skipping WebSocket connection during SSR');
        return;
      }
      
      // Skip if WebSocket is disabled due to too many failures
      if (isDisabled) {
        console.log('WebSocket connection disabled due to consecutive failures');
        return;
      }
      
      // Skip if already connected or connecting
      if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
        console.log('WebSocket already connected or connecting, skipping');
        return;
      }
      
      const urlsToTry = [url, ...fallbackUrls];
      const currentUrlToTry = urlsToTry[urlIndex.current];
      
      console.log(`Attempting to connect to WebSocket: ${currentUrlToTry} (attempt ${urlIndex.current + 1}/${urlsToTry.length})`);
      setCurrentUrl(currentUrlToTry);
      
      // Close existing connection if any
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      
      ws.current = new WebSocket(currentUrlToTry);
      
      // Set connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.current && ws.current.readyState === WebSocket.CONNECTING) {
          console.log('WebSocket connection timeout, closing...');
          ws.current.close();
        }
      }, 10000); // 10 second timeout
      
      ws.current.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        consecutiveFailures.current = 0; // Reset consecutive failures on successful connection
        urlIndex.current = 0; // Reset URL index on successful connection
        onOpen?.();
      };

      ws.current.onmessage = (event) => {
        try {
          // Check if the data is empty or not a string
          if (!event.data || typeof event.data !== 'string') {
            console.warn('Received invalid WebSocket message data:', event.data);
            return;
          }
          
          // Check if the data is empty or just whitespace
          const trimmedData = event.data.trim();
          if (!trimmedData) {
            console.warn('Received empty WebSocket message');
            return;
          }
          
          const message: WebSocketMessage = JSON.parse(trimmedData);
          onMessage?.(message);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err, 'Data:', event.data);
        }
      };

      ws.current.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log(`WebSocket closed: ${event.code} - ${event.reason}`);
        console.log(`WebSocket URL: ${currentUrlToTry}`);
        setIsConnected(false);
        onClose?.();
        
        // Don't try to reconnect if the connection was closed normally (code 1000)
        if (event.code === 1000) {
          console.log('WebSocket closed normally, not attempting reconnection');
          return;
        }
        
        // Try next URL if available
        const urlsToTry = [url, ...fallbackUrls];
        if (urlIndex.current < urlsToTry.length - 1) {
          urlIndex.current++;
          console.log(`Trying next URL: ${urlsToTry[urlIndex.current]}`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 1000); // Shorter delay for URL switching
        } else {
          // Reset URL index and try reconnection
          urlIndex.current = 0;
          
          // Attempt to reconnect if we haven't exceeded max attempts
          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current++;
            console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts}) in ${reconnectInterval}ms`);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else {
            console.log('Max reconnection attempts reached');
            consecutiveFailures.current++;
            
            // Disable WebSocket after 3 consecutive complete failure cycles
            if (consecutiveFailures.current >= 3) {
              console.log('Too many consecutive failures, disabling WebSocket connections');
              setIsDisabled(true);
              setError('WebSocket connection disabled due to repeated failures');
            } else {
              setError('Max reconnection attempts reached');
            }
          }
        }
      };

      ws.current.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('WebSocket error:', error);
        console.error('WebSocket URL:', currentUrlToTry);
        console.error('WebSocket ready state:', ws.current?.readyState);
        console.error('WebSocket error details:', {
          type: error.type,
          target: error.target,
          currentTarget: error.currentTarget,
          timeStamp: error.timeStamp
        });
        setError(`WebSocket connection error: ${currentUrlToTry}`);
        onError?.(error);
      };

    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setError('Failed to create WebSocket connection');
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    setIsConnected(false);
  };

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  };

  const enableWebSocket = () => {
    setIsDisabled(false);
    consecutiveFailures.current = 0;
    reconnectAttempts.current = 0;
    urlIndex.current = 0;
    setError(null);
    connect();
  };

  const testConnection = async () => {
    const urlsToTry = [url, ...fallbackUrls];
    console.log('Testing WebSocket connections...');
    
    for (let i = 0; i < urlsToTry.length; i++) {
      const testUrl = urlsToTry[i];
      console.log(`Testing connection to: ${testUrl}`);
      
      try {
        const testWs = new WebSocket(testUrl);
        
        const testResult = await new Promise<{ success: boolean; error?: string; url: string }>((resolve) => {
          const timeout = setTimeout(() => {
            testWs.close();
            resolve({ success: false, error: 'Connection timeout', url: testUrl });
          }, 5000);
          
          testWs.onopen = () => {
            clearTimeout(timeout);
            testWs.close();
            resolve({ success: true, url: testUrl });
          };
          
          testWs.onerror = (error) => {
            clearTimeout(timeout);
            resolve({ success: false, error: error.type, url: testUrl });
          };
        });
        
        console.log(`Test result for ${testUrl}:`, testResult);
        
        if (testResult.success) {
          console.log(`✅ WebSocket connection successful to: ${testUrl}`);
          return testResult;
        } else {
          console.log(`❌ WebSocket connection failed to: ${testUrl} - ${testResult.error}`);
        }
      } catch (err) {
        console.log(`❌ WebSocket connection error to: ${testUrl} - ${err}`);
      }
    }
    
    console.log('All WebSocket connection tests failed');
    return { success: false, error: 'All connections failed' };
  };

  useEffect(() => {
    // Only connect on client-side and when not in build mode
    if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'production') {
      connect();
    } else if (typeof window !== 'undefined') {
      // In production, add a small delay to ensure proper initialization
      const timer = setTimeout(() => {
        connect();
      }, 100);
      return () => clearTimeout(timer);
    }
    
    return () => {
      disconnect();
    };
  }, [url]); // Keep url dependency but now it should be stable due to memoization

  return {
    isConnected,
    error,
    currentUrl,
    isDisabled,
    sendMessage,
    disconnect,
    connect,
    enableWebSocket,
    testConnection
  };
};


