import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface WindData {
  location: string;
  speed: string;
  direction: string;
  gusts: string;
  status: string;
  timestamp: string;
  temperature?: string;
  humidity?: string;
}

const WindDataDisplay: React.FC = () => {
  const [windData, setWindData] = useState<WindData[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting');
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        console.log('Wind data WebSocket connected');
        setConnectionStatus('connected');
        setError('');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received WebSocket message:', data);
          
          if (data.type === 'wind_data_update' && data.wind_data) {
            setWindData(data.wind_data);
            setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
            console.log('Updated wind data:', data.wind_data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('Wind data WebSocket disconnected');
        setConnectionStatus('disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      
      ws.onerror = (error) => {
        console.error('Wind data WebSocket error details:', {
          type: error.type || 'websocket_error',
          timestamp: new Date().toISOString(),
          message: 'Wind data WebSocket connection failed'
        });
        setConnectionStatus('error');
        setError('リアルタイム接続エラー');
      };
      
      return ws;
    };

    const websocket = connectWebSocket();
    
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'normal': return '正常';
      case 'moderate': return '注意';
      case 'calm': return '穏やか';
      case 'error': return 'エラー';
      default: return status;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'normal': return 'default';
      case 'moderate': return 'secondary';
      case 'calm': return 'outline';
      case 'error': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span>💨 風況データ</span>
          <div className="flex items-center gap-2">
            {connectionStatus === 'connected' && (
              <Badge variant="outline" className="text-xs">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                LIVE
              </Badge>
            )}
            {lastUpdate && (
              <span className="text-xs text-gray-500">
                更新: {lastUpdate}
              </span>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
        
        {connectionStatus === 'connecting' && (
          <div className="text-center py-8">
            <p className="text-gray-500">風況データを読み込み中...</p>
          </div>
        )}
        
        {windData.length === 0 && connectionStatus !== 'connecting' && (
          <div className="text-center py-8">
            <p className="text-gray-500">風況データを取得できません</p>
          </div>
        )}
        
        {windData.length > 0 && (
          <>
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-600 text-sm">
                📡 リアルタイムで10秒ごとに更新されています
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {windData.map((data, index) => (
                <div key={`${data.location}-${index}`} className="border rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-semibold">{data.location}</h3>
                    <Badge variant={getStatusVariant(data.status)}>
                      {getStatusLabel(data.status)}
                    </Badge>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div>風速: {data.speed}</div>
                    <div>風向: {data.direction}</div>
                    <div>最大瞬間風速: {data.gusts}</div>
                    {data.temperature && <div>気温: {data.temperature}</div>}
                    {data.humidity && <div>湿度: {data.humidity}</div>}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default WindDataDisplay; 