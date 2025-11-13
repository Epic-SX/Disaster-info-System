'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { apiClient, API_ENDPOINTS, createWebSocket, WS_ENDPOINTS } from '@/lib/api-config';

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

  // Fallback HTTP polling function
  const startHttpPolling = useCallback(() => {
    console.log('Starting HTTP polling for disaster data');
    const pollInterval = setInterval(async () => {
      // Inline the fetch to avoid dependency issues
      setLoading(true);
      setError(null);
      
      try {
        // Fetch from your backend API which aggregates disaster data using the new API client
        const [earthquakeResponse, tsunamiResponse] = await Promise.allSettled([
          apiClient.get(API_ENDPOINTS.earthquake.recent),
          apiClient.get(API_ENDPOINTS.tsunami.alerts)
        ]);

        if (earthquakeResponse.status === 'fulfilled') {
          const earthquakeData = earthquakeResponse.value;
          setEarthquakes(earthquakeData.slice(0, 50)); // Limit to 50 recent earthquakes
        }

        if (tsunamiResponse.status === 'fulfilled') {
          const tsunamiData = tsunamiResponse.value;
          setTsunamis(tsunamiData.slice(0, 20)); // Limit to 20 tsunami alerts
        }

        setLastUpdate(new Date());
      } catch (err) {
        setError('災害データの取得に失敗しました');
        console.error('Failed to fetch disaster data:', err);
      } finally {
        setLoading(false);
      }
    }, 15000); // Poll every 15 seconds

    return pollInterval;
  }, []);

  const connectWebSocket = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 2; // Reduced to fail faster
    let initialTimeout: NodeJS.Timeout;
    
    try {
      setConnectionStatus('connecting');
      const ws = createWebSocket(WS_ENDPOINTS.main);
      
      // Handle case where WebSocket creation fails or is not available
      if (!ws) {
        console.log('WebSocket not available, falling back to HTTP polling');
        setConnectionStatus('disconnected');
        startHttpPolling();
        return;
      }
      
      wsRef.current = ws;

      // Set a faster timeout for initial connection
      initialTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.log('Earthquake WebSocket initial connection timeout, falling back to HTTP polling');
          ws.close();
          startHttpPolling();
        }
      }, 5000); // 5 second timeout

      ws.onopen = () => {
        clearTimeout(initialTimeout);
        console.log('Earthquake WebSocket connected');
        setConnectionStatus('connected');
        setError(null);
        reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received WebSocket message:', data);
          
          if (data.type === 'earthquake_data_update' || data.type === 'earthquake_update') {
            setEarthquakes(data.earthquakes || data.data || []);
            setLastUpdate(new Date());
            console.log('Updated earthquake data:', data.earthquakes || data.data);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = (event) => {
        clearTimeout(initialTimeout);
        console.log('🔄 災害監視WebSocket切断 - HTTPポーリングに切替中');
        setConnectionStatus('disconnected');
        
        // Only attempt reconnect if we haven't exceeded max attempts and it's not a proxy error (1006)
        if (reconnectAttempts < maxReconnectAttempts && event.code !== 1006) {
          reconnectAttempts++;
          console.log(`🔄 WebSocket再接続試行 ${reconnectAttempts}/${maxReconnectAttempts}`);
          setTimeout(() => connectWebSocket(), 3000); // Faster reconnect
        } else {
          console.log('✅ HTTPポーリングモードで災害監視を継続中');
          startHttpPolling();
        }
      };

      ws.onerror = (error) => {
        clearTimeout(initialTimeout);
        console.log('🔄 WebSocket接続エラー - HTTPポーリングに切替中');
        setConnectionStatus('disconnected');
        
        // Immediately try HTTP polling on error
        setTimeout(() => {
          startHttpPolling();
        }, 1000);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnectionStatus('disconnected');
      startHttpPolling();
    }
  }, [startHttpPolling]);

  useEffect(() => {
    // Set mounted state to handle client-side rendering
    setIsMounted(true);
    
    // Initial data fetch
    fetchDisasterData();
    
    // Connect WebSocket
    connectWebSocket();
    
    // Set up periodic refresh
    const interval = setInterval(fetchDisasterData, 300000);
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const fetchDisasterData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch from your backend API which aggregates disaster data using the new API client
      const [earthquakeResponse, tsunamiResponse] = await Promise.allSettled([
        apiClient.get(API_ENDPOINTS.earthquake.recent),
        apiClient.get(API_ENDPOINTS.tsunami.alerts)
      ]);

      if (earthquakeResponse.status === 'fulfilled') {
        const earthquakeData = earthquakeResponse.value;
        setEarthquakes(earthquakeData.slice(0, 50)); // Limit to 50 recent earthquakes
      }

      if (tsunamiResponse.status === 'fulfilled') {
        const tsunamiData = tsunamiResponse.value;
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
    <Card className="h-full bg-gradient-to-br from-slate-900 to-slate-800 text-white border-slate-700">
      <CardHeader className="bg-gradient-to-r from-red-600 to-orange-600">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          🚨 リアルタイム災害監視システム
          <div className="flex items-center gap-2 ml-auto">
            <div className="flex items-center gap-1 text-sm">
              {getConnectionIcon()}
              <span className="text-xs font-bold">
                {connectionStatus === 'connected' ? '🔴 LIVE' : getConnectionText()}
              </span>
            </div>
            <Button
              onClick={fetchDisasterData}
              disabled={loading}
              size="sm"
              variant="outline"
              className="border-white/20 text-white hover:bg-white/10"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              更新
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="space-y-6">
          {error && (
            <Alert className="border-red-400 bg-red-900/50 text-red-100">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <AlertDescription className="text-red-100">
                ⚠️ {error}
              </AlertDescription>
            </Alert>
          )}

          {/* 緊急アラート表示 */}
          {earthquakes.some(eq => eq.magnitude >= 6.0) && (
            <div className="bg-red-600 border-2 border-red-400 rounded-lg p-4 animate-pulse">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🚨</span>
                <div>
                  <div className="font-bold text-lg">緊急地震速報</div>
                  <div className="text-sm">大規模地震を検出しました</div>
                </div>
              </div>
            </div>
          )}

          {/* メインマップ表示 */}
          <div className="relative h-96 rounded-lg overflow-hidden border-2 border-slate-600">
            <MapWithNoSSR
              earthquakes={earthquakes}
              tsunamis={tsunamis}
              onMapReady={() => setMapReady(true)}
            />
            
            {/* ライブ配信用オーバーレイ */}
            <div className="absolute top-4 left-4 bg-black/70 rounded-lg p-3">
              <div className="text-xs text-gray-300">災害情報システム</div>
              <div className="text-lg font-bold text-white">
                🌊 リアルタイム監視中
              </div>
              {lastUpdate && (
                <div className="text-xs text-gray-400">
                  最終更新: {lastUpdate.toLocaleTimeString('ja-JP')}
                </div>
              )}
            </div>

            {/* 接続状況インジケーター */}
            <div className="absolute top-4 right-4">
              {connectionStatus === 'connected' && (
                <div className="bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                  <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                  LIVE配信中
                </div>
              )}
            </div>
          </div>

          {/* ダッシュボード情報パネル */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 地震活動統計 */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg p-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">{earthquakes.length}</div>
                <div className="text-blue-100 text-sm">検出中の地震</div>
                <div className="text-xs text-blue-200 mt-1">
                  最大M{earthquakes.length > 0 ? Math.max(...earthquakes.map(eq => eq.magnitude)).toFixed(1) : '0.0'}
                </div>
              </div>
            </div>

            {/* 津波警報状況 */}
            <div className="bg-gradient-to-br from-orange-600 to-red-600 rounded-lg p-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">{tsunamis.length}</div>
                <div className="text-orange-100 text-sm">津波警報</div>
                <div className="text-xs text-orange-200 mt-1">
                  {tsunamis.length > 0 ? '⚠️ 警戒中' : '✅ 正常'}
                </div>
              </div>
            </div>

            {/* システム状況 */}
            <div className="bg-gradient-to-br from-green-600 to-emerald-600 rounded-lg p-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">
                  {connectionStatus === 'connected' ? '100%' : '0%'}
                </div>
                <div className="text-green-100 text-sm">システム稼働率</div>
                <div className="text-xs text-green-200 mt-1">
                  {connectionStatus === 'connected' ? '🟢 オンライン' : '🔴 オフライン'}
                </div>
              </div>
            </div>
          </div>
          
          {/* 最新地震情報リスト（放送用） */}
          {earthquakes.length > 0 && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-600">
              <h4 className="font-bold mb-3 flex items-center gap-2 text-white">
                📊 最新地震情報
                {connectionStatus === 'connected' && (
                  <Badge className="bg-red-600 text-white text-xs animate-pulse">
                    🔴 LIVE更新
                  </Badge>
                )}
              </h4>
              <div className="space-y-3">
                {earthquakes.slice(0, 5).map((earthquake) => (
                  <div key={earthquake.id} className="flex justify-between items-center p-3 bg-slate-700 rounded border-l-4 border-orange-500">
                    <div className="flex-1">
                      <div className="font-bold text-white text-lg">{earthquake.location}</div>
                      <div className="text-gray-300 text-sm">
                        <span className="bg-red-600 text-white px-2 py-1 rounded text-xs font-bold mr-2">
                          M{earthquake.magnitude}
                        </span>
                        {getIntensityLabel(earthquake.intensity)} • 深さ{earthquake.depth}km
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-white font-medium">{formatTime(earthquake.time)}</div>
                      {earthquake.tsunami && (
                        <Badge className="bg-blue-600 text-white text-xs mt-1">
                          🌊 津波注意
                        </Badge>
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