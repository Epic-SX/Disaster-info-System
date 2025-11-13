import React, { useState, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { getWebSocketConfig } from '../config/websocket';

const WebSocketDebugPanel: React.FC = () => {
  const [testResults, setTestResults] = useState<any[]>([]);
  
  // Memoize WebSocket configuration to prevent unnecessary re-renders
  const wsConfig = useMemo(() => getWebSocketConfig(), []);
  
  const { 
    isConnected, 
    error, 
    currentUrl, 
    isDisabled, 
    testConnection,
    enableWebSocket 
  } = useWebSocket({
    url: wsConfig.url,
    fallbackUrls: wsConfig.fallbackUrls,
    onMessage: (message) => {
      console.log('Debug panel received message:', message);
    },
    onOpen: () => {
      console.log('Debug panel WebSocket connected');
    },
    onClose: () => {
      console.log('Debug panel WebSocket disconnected');
    },
    onError: (error) => {
      console.error('Debug panel WebSocket error:', error);
    }
  });

  const handleTestConnection = async () => {
    console.log('Starting WebSocket connection test...');
    const result = await testConnection();
    setTestResults(prev => [...prev, { ...result, timestamp: new Date().toISOString() }]);
  };

  const clearResults = () => {
    setTestResults([]);
  };

  return (
    <div style={{ 
      position: 'fixed', 
      top: '10px', 
      right: '10px', 
      background: 'white', 
      border: '1px solid #ccc', 
      padding: '10px', 
      borderRadius: '5px',
      maxWidth: '400px',
      zIndex: 9999,
      fontSize: '12px'
    }}>
      <h4>WebSocket Debug Panel</h4>
      
      <div style={{ marginBottom: '10px' }}>
        <strong>Status:</strong> {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>
      
      <div style={{ marginBottom: '10px' }}>
        <strong>Current URL:</strong> {currentUrl}
      </div>
      
      <div style={{ marginBottom: '10px' }}>
        <strong>Disabled:</strong> {isDisabled ? 'Yes' : 'No'}
      </div>
      
      {error && (
        <div style={{ marginBottom: '10px', color: 'red' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      
      <div style={{ marginBottom: '10px' }}>
        <button onClick={handleTestConnection} style={{ marginRight: '5px' }}>
          Test Connection
        </button>
        <button onClick={clearResults}>
          Clear Results
        </button>
        {isDisabled && (
          <button onClick={enableWebSocket} style={{ marginLeft: '5px' }}>
            Enable WebSocket
          </button>
        )}
      </div>
      
      <div>
        <strong>Test Results:</strong>
        {testResults.length === 0 ? (
          <div>No tests run yet</div>
        ) : (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {testResults.map((result, index) => (
              <div key={index} style={{ 
                marginBottom: '5px', 
                padding: '5px', 
                background: result.success ? '#d4edda' : '#f8d7da',
                borderRadius: '3px'
              }}>
                <div><strong>{result.success ? '✅' : '❌'}</strong> {result.url}</div>
                <div style={{ fontSize: '10px' }}>
                  {new Date(result.timestamp).toLocaleTimeString()}
                </div>
                {result.error && (
                  <div style={{ fontSize: '10px', color: 'red' }}>
                    Error: {result.error}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div style={{ marginTop: '10px', fontSize: '10px' }}>
        <strong>Available URLs:</strong>
        <div>Primary: {wsConfig.url}</div>
        {wsConfig.fallbackUrls.map((url, index) => (
          <div key={index}>Fallback {index + 1}: {url}</div>
        ))}
      </div>
    </div>
  );
};

export default WebSocketDebugPanel;
