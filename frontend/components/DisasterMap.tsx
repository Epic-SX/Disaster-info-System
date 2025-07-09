'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import dynamic from 'next/dynamic';
import { 
  MapPin, 
  RefreshCw, 
  AlertTriangle, 
  Zap, 
  Wifi, 
  WifiOff 
} from 'lucide-react';

// Dynamically import Leaflet CSS and components to avoid SSR issues
const MapWithNoSSR = dynamic(() => import('./MapComponent'), {
  ssr: false,
  loading: () => (
    <div className="h-96 rounded-lg overflow-hidden border bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-2">🗾</div>
        <div className="text-lg font-semibold">マップを読み込み中...</div>
      </div>
    </div>
  )
});

const JAPAN_CENTER = {
  lat: 36.2048,
  lng: 138.2529
};

interface EarthquakeData {
  id: string;
  time: string;
  location: string;
  magnitude: number;
  depth: number;
  latitude: number;
  longitude: number;
  intensity: string;
  tsunami?: boolean;
}

interface TsunamiInfo {
  id: string;
  location: string;
  level: string;
  time: string;
  latitude: number;
  longitude: number;
}

const DisasterMap: React.FC = () => {
  const [mapReady, setMapReady] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [earthquakes, setEarthquakes] = useState<EarthquakeData[]>([]);
  const [tsunamis, setTsunamis] = useState<TsunamiInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Set mounted state to handle client-side rendering
    setIsMounted(true);
    
    // Initial data fetch
    fetchDisasterData();
    
    // Connect to WebSocket for real-time updates
    connectWebSocket();
    
    // Refresh data every 5 minutes as backup
    const interval = setInterval(fetchDisasterData, 300000);
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      setConnectionStatus('connecting');
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Earthquake WebSocket connected');
        setConnectionStatus('connected');
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received WebSocket message:', data);
          
          if (data.type === 'earthquake_update') {
            setEarthquakes(data.data);
            setLastUpdate(new Date());
            console.log('Updated earthquake data:', data.data);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('Earthquake WebSocket disconnected:', event.code, event.reason);
        setConnectionStatus('disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      ws.onerror = (error) => {
        console.error('Earthquake WebSocket error:', {
          type: error.type,
          target: error.target?.url || 'Unknown',
          readyState: error.target?.readyState || 'Unknown',
          timestamp: new Date().toISOString()
        });
        setConnectionStatus('disconnected');
        setError('リアルタイム接続エラー');
      };

    } catch (err) {
      console.error('Failed to connect to WebSocket:', err);
      setConnectionStatus('disconnected');
      setError('WebSocket接続に失敗しました');
    }
  };

  const fetchDisasterData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch from your backend API which aggregates disaster data
      const [earthquakeResponse, tsunamiResponse] = await Promise.allSettled([
        fetch('http://localhost:8000/api/earthquake/recent'),
        fetch('http://localhost:8000/api/tsunami/alerts')
      ]);

      if (earthquakeResponse.status === 'fulfilled' && earthquakeResponse.value.ok) {
        const earthquakeData = await earthquakeResponse.value.json();
        setEarthquakes(earthquakeData.slice(0, 50)); // Limit to 50 recent earthquakes
      }

      if (tsunamiResponse.status === 'fulfilled' && tsunamiResponse.value.ok) {
        const tsunamiData = await tsunamiResponse.value.json();
        setTsunamis(tsunamiData.slice(0, 20)); // Limit to 20 tsunami alerts
      }

      setLastUpdate(new Date());
    } catch (err) {
      setError('災害データの取得に失敗しました');
      console.error('Failed to fetch disaster data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'connecting':
        return <RefreshCw className="h-4 w-4 text-yellow-500 animate-spin" />;
      case 'disconnected':
        return <WifiOff className="h-4 w-4 text-red-500" />;
    }
  };

  const getConnectionText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'リアルタイム接続中';
      case 'connecting':
        return '接続中...';
      case 'disconnected':
        return '接続エラー';
    }
  };

  const getMagnitudeColor = (magnitude: number) => {
    if (magnitude >= 7) return '#ff0000'; // Red for major earthquakes
    if (magnitude >= 6) return '#ff4500'; // Orange-red
    if (magnitude >= 5) return '#ff8c00'; // Orange
    if (magnitude >= 4) return '#ffd700'; // Gold
    if (magnitude >= 3) return '#9acd32'; // Yellow-green
    return '#32cd32'; // Green for minor earthquakes
  };

  const getMagnitudeRadius = (magnitude: number) => {
    return Math.max(magnitude * 5000, 10000); // Minimum 10km radius
  };

  const getIntensityLabel = (intensity: string) => {
    const intensityMap: { [key: string]: string } = {
      '1': '震度1',
      '2': '震度2',
      '3': '震度3',
      '4': '震度4',
      '5-': '震度5弱',
      '5+': '震度5強',
      '6-': '震度6弱',
      '6+': '震度6強',
      '7': '震度7'
    };
    return intensityMap[intensity] || intensity;
  };

  const formatTime = (timeString: string) => {
    try {
      return new Date(timeString).toLocaleString('ja-JP');
    } catch {
      return timeString;
    }
  };

  if (!isMounted) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            災害マップ
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-100 h-96 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-2">🗾</div>
              <div className="text-lg font-semibold">マップを読み込み中...</div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          災害マップ
          <div className="flex items-center gap-2 ml-auto">
            <div className="flex items-center gap-1 text-sm">
              {getConnectionIcon()}
              <span className="text-xs">{getConnectionText()}</span>
            </div>
            <Button
              onClick={fetchDisasterData}
              disabled={loading}
              size="sm"
              variant="outline"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              更新
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {error && (
            <Alert className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-600">
                {error}
              </AlertDescription>
            </Alert>
          )}

          {/* Map Container */}
          <div className="h-96 rounded-lg overflow-hidden border">
            <MapWithNoSSR
              earthquakes={earthquakes}
              tsunamis={tsunamis}
              onMapReady={() => setMapReady(true)}
            />
          </div>

          {/* Legend and Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold mb-2">凡例</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-red-500"></div>
                  <span>M7.0以上（大地震）</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-orange-500"></div>
                  <span>M6.0-6.9（強い地震）</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
                  <span>M5.0-5.9（中程度の地震）</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-green-500"></div>
                  <span>M5.0未満（軽微な地震）</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-blue-600">🌊</div>
                  <span>津波情報</span>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="font-semibold mb-2">データ状況</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>地震情報:</span>
                  <span className="font-medium">{earthquakes.length}件</span>
                </div>
                <div className="flex justify-between">
                  <span>津波情報:</span>
                  <span className="font-medium">{tsunamis.length}件</span>
                </div>
                {lastUpdate && (
                  <div className="flex justify-between">
                    <span>最終更新:</span>
                    <span className="font-medium text-xs">
                      {lastUpdate.toLocaleTimeString('ja-JP')}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>接続状況:</span>
                  <span className="font-medium flex items-center gap-1">
                    {getConnectionIcon()}
                    <span className="text-xs">{getConnectionText()}</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Recent Events Summary */}
          {earthquakes.length > 0 && (
            <div>
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                最近の地震活動
                {connectionStatus === 'connected' && (
                  <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                    ライブ更新中
                  </Badge>
                )}
              </h4>
          <div className="space-y-2">
                {earthquakes.slice(0, 3).map((earthquake) => (
                  <div key={earthquake.id} className="flex justify-between items-center p-2 border rounded">
                <div>
                      <div className="font-medium">{earthquake.location}</div>
                      <div className="text-sm text-gray-600">
                        M{earthquake.magnitude} • {getIntensityLabel(earthquake.intensity)} • {earthquake.depth}km
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <div>{formatTime(earthquake.time)}</div>
                      {earthquake.tsunami && (
                        <Badge className="bg-red-500 text-white text-xs">津波</Badge>
                      )}
                </div>
              </div>
            ))}
          </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default DisasterMap; 