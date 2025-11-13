'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wind, Thermometer, Droplets, Gauge } from 'lucide-react'
import { createWebSocket, WS_ENDPOINTS } from '@/lib/api-config'

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
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Only create WebSocket connection on client side
    if (typeof window === 'undefined') return;
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 2; // Reduced from 3 to fail faster
    let pollingInterval: NodeJS.Timeout | null = null;
    
    const connectWebSocket = () => {
      let initialTimeout: NodeJS.Timeout;
      
      try {
        const ws = createWebSocket(WS_ENDPOINTS.main);
        
        // Handle case where WebSocket creation fails or is not available
        if (!ws) {
          console.log('WebSocket not available for wind data, falling back to HTTP polling');
          setConnectionStatus('disconnected');
          startHttpPolling();
          return;
        }
        
        wsRef.current = ws;
        setConnectionStatus('connecting');

        // Set a faster timeout for initial connection
        initialTimeout = setTimeout(() => {
          if (ws.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket initial connection timeout, falling back to HTTP polling');
            ws.close();
            startHttpPolling();
          }
        }, 5000); // 5 second timeout for initial connection

        ws.onopen = () => {
          clearTimeout(initialTimeout);
          console.log('Wind WebSocket connected');
          setConnectionStatus('connected');
          reconnectAttempts = 0;
          setError('');
          
          // Stop HTTP polling if it was running
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'wind_data_update' || data.type === 'wind_update' || data.type === 'amedas_update') {
              setWindData(data.wind_data || data.data || data.amedas_data || []);
              setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
              setError(''); // Clear any previous errors
            }
          } catch (err) {
            console.error('Error parsing wind WebSocket message:', err);
          }
        };

        ws.onclose = (event) => {
          clearTimeout(initialTimeout);
          console.log('🌪️ 風況監視WebSocket切断 - HTTPポーリングに切替中');
          setConnectionStatus('disconnected');
          
          // Only attempt reconnect if we haven't exceeded max attempts and it's not a proxy error
          if (reconnectAttempts < maxReconnectAttempts && event.code !== 1006) {
            reconnectAttempts++;
            console.log(`🔄 風況WebSocket再接続試行 ${reconnectAttempts}/${maxReconnectAttempts}`);
            setTimeout(connectWebSocket, 3000); // Faster reconnect
          } else {
            console.log('✅ HTTPポーリングモードで風況監視を継続中');
            startHttpPolling();
          }
        };

        ws.onerror = (error) => {
          clearTimeout(initialTimeout);
          console.log('🔄 風況WebSocket接続エラー - HTTPポーリングに切替中');
          setConnectionStatus('error');
          setError('WebSocket connection error');
          
          // Immediately try HTTP polling on error
          setTimeout(() => {
            startHttpPolling();
          }, 1000);
        };
      } catch (error) {
        console.error('Failed to connect wind WebSocket:', error);
        setConnectionStatus('error');
        setError('Failed to establish WebSocket connection');
        startHttpPolling();
      }
    };

    // Fallback HTTP polling function
    const startHttpPolling = () => {
      if (pollingInterval) return; // Already polling
      
      console.log('Starting HTTP polling for AMeDAS weather data from JSON export');
      setConnectionStatus('connected');
      setError('');
      
      // Initial fetch
      fetchWindDataHTTP();
      
      pollingInterval = setInterval(fetchWindDataHTTP, 10000); // Poll every 10 seconds
    };

    const fetchWindDataHTTP = async () => {
      try {
        // Fetch wind data from JSON export endpoint
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/weather/wind`);
        if (response.ok) {
          const data = await response.json();
          // Limit to first 50 stations for display
          setWindData(data.slice(0, 50));
          setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
          setConnectionStatus('connected');
          setError(''); // Clear any previous errors
        } else {
          console.error('HTTP polling failed:', response.status);
          setError('Failed to fetch wind data');
        }
      } catch (err) {
        console.error('HTTP polling error:', err);
        setError('Connection error');
      }
    };

    // Try WebSocket first, but be ready to fall back quickly
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pollingInterval) {
        clearInterval(pollingInterval);
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
    <Card className="bg-gradient-to-br from-cyan-900 to-blue-900 text-white border-cyan-700">
      <CardHeader className="bg-gradient-to-r from-cyan-600 to-blue-600">
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wind className="h-6 w-6" />
            🌡️ AMeDAS リアルタイム気象観測
          </span>
          <div className="flex items-center gap-3">
            {connectionStatus === 'connected' && (
              <Badge className="bg-green-600 text-white text-xs font-bold animate-pulse">
                <span className="w-2 h-2 bg-white rounded-full mr-1 animate-pulse"></span>
                🔴 LIVE配信
              </Badge>
            )}
            {lastUpdate && (
              <span className="text-xs text-cyan-100">
                更新: {lastUpdate}
              </span>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-900/50 border border-red-400 rounded-lg">
            <p className="text-red-100 text-sm font-medium">⚠️ {error}</p>
          </div>
        )}
        
        {connectionStatus === 'connecting' && (
          <div className="text-center py-8">
            <div className="animate-spin text-4xl mb-4">💨</div>
            <p className="text-cyan-200 text-lg font-medium">風況データを読み込み中...</p>
          </div>
        )}
        
        {windData.length === 0 && connectionStatus !== 'connecting' && (
          <div className="text-center py-8">
            <div className="text-4xl mb-4">🌪️</div>
            <p className="text-cyan-300 text-lg">風況データを取得できません</p>
          </div>
        )}
        
        {windData.length > 0 && (
          <>
            {/* システム稼働状況 */}
            <div className="mb-6 p-4 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg text-center">
              <div className="text-2xl font-bold">🟢 AMeDAS気象観測システム稼働中</div>
              <div className="text-sm mt-1 text-green-100">
                📡 毎時更新（JMAからスクレイピング） • 全国{windData.length}観測所データ表示中
              </div>
            </div>
            
            {/* 風況データグリッド */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {windData.map((data, index) => (
                <div key={`${data.location}-${index}`} 
                     className="bg-gradient-to-br from-slate-800 to-slate-700 border-2 border-cyan-500/30 rounded-lg p-4 hover:border-cyan-400 transition-all duration-300">
                  
                  {/* 地点ヘッダー */}
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-bold text-lg text-white flex items-center gap-2">
                      📍 {data.location}
                    </h3>
                    <Badge 
                      className={`text-xs font-bold ${
                        data.status === 'normal' ? 'bg-green-600' :
                        data.status === 'moderate' ? 'bg-yellow-600' :
                        data.status === 'error' ? 'bg-red-600' :
                        'bg-gray-600'
                      }`}
                    >
                      {getStatusLabel(data.status)}
                    </Badge>
                  </div>
                  
                  {/* 風速メイン表示 */}
                  <div className="mb-4 text-center">
                    <div className="text-3xl font-bold text-cyan-300 mb-1">
                      {data.speed}
                    </div>
                    <div className="text-sm text-cyan-200">現在の風速</div>
                  </div>
                  
                  {/* 詳細データ */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-blue-900/50 rounded p-2 text-center">
                      <div className="text-blue-200 text-xs">風向</div>
                      <div className="font-bold text-white">{data.direction}</div>
                    </div>
                    <div className="bg-orange-900/50 rounded p-2 text-center">
                      <div className="text-orange-200 text-xs">最大瞬間風速</div>
                      <div className="font-bold text-white">{data.gusts}</div>
                    </div>
                    {data.temperature && (
                      <div className="bg-red-900/50 rounded p-2 text-center">
                        <div className="text-red-200 text-xs">
                          <Thermometer className="h-3 w-3 inline mr-1" />
                          気温
                        </div>
                        <div className="font-bold text-white">{data.temperature}</div>
                      </div>
                    )}
                    {data.humidity && (
                      <div className="bg-purple-900/50 rounded p-2 text-center">
                        <div className="text-purple-200 text-xs">
                          <Droplets className="h-3 w-3 inline mr-1" />
                          湿度
                        </div>
                        <div className="font-bold text-white">{data.humidity}</div>
                      </div>
                    )}
                  </div>
                  
                  {/* 強風警告 */}
                  {parseFloat(data.speed.replace(/[^\d.]/g, '')) > 15 && (
                    <div className="mt-3 bg-red-600 text-white p-2 rounded text-center text-xs font-bold animate-pulse">
                      ⚠️ 強風注意
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* 全体統計 */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-white">{windData.length}</div>
                <div className="text-blue-100 text-sm">監視地点数</div>
              </div>
              <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-white">
                  {Math.max(...windData.map(d => parseFloat(d.speed.replace(/[^\d.]/g, '')) || 0)).toFixed(1)}
                </div>
                <div className="text-green-100 text-sm">最大風速 (km/h)</div>
              </div>
              <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-white">
                  {windData.filter(d => d.status === 'normal').length}
                </div>
                <div className="text-purple-100 text-sm">正常稼働地点</div>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default WindDataDisplay; 