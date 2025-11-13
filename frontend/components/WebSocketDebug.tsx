import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '../hooks/useWebSocket';
import { getWebSocketConfig } from '../config/websocket';

const WebSocketDebug: React.FC = () => {
  // Memoize WebSocket configuration to prevent unnecessary re-renders
  const wsConfig = useMemo(() => getWebSocketConfig(), []);

  const { 
    isConnected, 
    error, 
    currentUrl, 
    isDisabled, 
    enableWebSocket,
    disconnect,
    connect 
  } = useWebSocket({
    url: wsConfig.url,
    fallbackUrls: wsConfig.fallbackUrls,
    onMessage: (message) => {
      console.log('WebSocket message received:', message);
    },
    onOpen: () => {
      console.log('WebSocket connected');
    },
    onClose: () => {
      console.log('WebSocket disconnected');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    }
  });

  const getStatusColor = () => {
    if (isDisabled) return 'bg-gray-500';
    if (isConnected) return 'bg-green-500';
    if (error) return 'bg-red-500';
    return 'bg-yellow-500';
  };

  const getStatusText = () => {
    if (isDisabled) return 'Disabled';
    if (isConnected) return 'Connected';
    if (error) return 'Error';
    return 'Connecting';
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-lg font-bold">WebSocket Debug</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
          <span className="font-medium">{getStatusText()}</span>
        </div>
        
        <div className="text-sm text-gray-600">
          <div><strong>URL:</strong> {currentUrl}</div>
          <div><strong>Primary:</strong> {wsConfig.url}</div>
          <div><strong>Fallbacks:</strong> {wsConfig.fallbackUrls.length}</div>
        </div>
        
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
            <strong>Error:</strong> {error}
          </div>
        )}
        
        <div className="flex gap-2">
          {isDisabled ? (
            <Button onClick={enableWebSocket} size="sm">
              Re-enable WebSocket
            </Button>
          ) : (
            <>
              <Button onClick={connect} size="sm" disabled={isConnected}>
                Connect
              </Button>
              <Button onClick={disconnect} size="sm" disabled={!isConnected}>
                Disconnect
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default WebSocketDebug;