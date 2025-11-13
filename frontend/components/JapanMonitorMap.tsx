'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Badge } from "@/components/ui/badge";
import dynamic from 'next/dynamic';
import { apiClient, API_ENDPOINTS, createWebSocket, WS_ENDPOINTS } from '@/lib/api-config';

// Dynamically import Leaflet to avoid SSR issues
const MapWithNoSSR = dynamic(() => import('./JapanPGAMapComponent'), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-screen flex items-center justify-center bg-gray-900">
      <div className="text-center text-white">
        <div className="text-6xl mb-4">🗾</div>
        <div className="text-2xl font-bold">リアルタイム災害監視システム</div>
        <div className="text-lg mt-2">マップを読み込み中...</div>
      </div>
    </div>
  )
});

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

interface PGADataPoint {
  id: string;
  latitude: number;
  longitude: number;
  pga: number; // Peak Ground Acceleration in gal
  location: string;
}

const JapanMonitorMap: React.FC = () => {
  const [isMounted, setIsMounted] = useState(false);
  const [earthquakes, setEarthquakes] = useState<EarthquakeData[]>([]);
  const [pgaData, setPgaData] = useState<PGADataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const updateIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Generate PGA data from earthquake data
  const generatePGAData = useCallback((earthquakes: EarthquakeData[]): PGADataPoint[] => {
    const pgaPoints: PGADataPoint[] = [];
    
    // For each earthquake, generate surrounding PGA observation points
    earthquakes.forEach((eq) => {
      const numPoints = Math.min(Math.floor(eq.magnitude * 10), 50); // More points for larger earthquakes
      
      for (let i = 0; i < numPoints; i++) {
        // Generate points in a radius around the epicenter
        const angle = (Math.PI * 2 * i) / numPoints;
        const distance = Math.random() * (eq.magnitude * 0.5); // Distance in degrees
        
        const lat = eq.latitude + Math.cos(angle) * distance;
        const lng = eq.longitude + Math.sin(angle) * distance;
        
        // Calculate PGA based on distance from epicenter (simplified model)
        const distanceKm = distance * 111; // Rough conversion to km
        const pga = Math.max(
          0.1,
          (eq.magnitude * 50) / Math.max(1, Math.sqrt(distanceKm + 10))
        );
        
        pgaPoints.push({
          id: `pga-${eq.id}-${i}`,
          latitude: lat,
          longitude: lng,
          pga: pga,
          location: eq.location
        });
      }
    });
    
    // Add some baseline monitoring stations across Japan
    const baselineStations = [
      { lat: 43.064, lng: 141.347, name: '札幌' },
      { lat: 40.824, lng: 140.740, name: '青森' },
      { lat: 38.268, lng: 140.872, name: '仙台' },
      { lat: 36.341, lng: 140.447, name: '水戸' },
      { lat: 35.689, lng: 139.692, name: '東京' },
      { lat: 35.443, lng: 139.638, name: '横浜' },
      { lat: 35.018, lng: 135.756, name: '京都' },
      { lat: 34.693, lng: 135.502, name: '大阪' },
      { lat: 34.397, lng: 132.459, name: '広島' },
      { lat: 33.590, lng: 130.402, name: '福岡' },
      { lat: 31.596, lng: 130.557, name: '鹿児島' },
      { lat: 26.212, lng: 127.681, name: '那覇' }
    ];
    
    baselineStations.forEach((station, idx) => {
      const backgroundPGA = 0.1 + Math.random() * 0.5; // Low background noise
      pgaPoints.push({
        id: `station-${idx}`,
        latitude: station.lat,
        longitude: station.lng,
        pga: backgroundPGA,
        location: station.name
      });
    });
    
    return pgaPoints;
  }, []);

  // Fallback HTTP polling function
  const startHttpPolling = useCallback(() => {
    console.log('Starting HTTP polling for disaster data');
    
    const pollInterval = setInterval(async () => {
      setLoading(true);
      setError(null);
      
      try {
        const earthquakeResponse = await apiClient.get(API_ENDPOINTS.earthquake.recent);
        const earthquakeData = earthquakeResponse.slice(0, 50);
        
        setEarthquakes(earthquakeData);
        
        // Generate PGA data from earthquake data
        const newPgaData = generatePGAData(earthquakeData);
        setPgaData(newPgaData);
        
        setLastUpdate(new Date());
      } catch (err) {
        console.error('Failed to fetch disaster data:', err);
        setError('データの取得に失敗しました');
      } finally {
        setLoading(false);
      }
    }, 15000); // Poll every 15 seconds

    updateIntervalRef.current = pollInterval;
  }, [generatePGAData]);

  const connectWebSocket = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    try {
      setConnectionStatus('connecting');
      const ws = createWebSocket(WS_ENDPOINTS.main);
      
      if (!ws) {
        console.log('WebSocket not available, falling back to HTTP polling');
        setConnectionStatus('disconnected');
        startHttpPolling();
        return;
      }
      
      wsRef.current = ws;

      const initialTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.log('WebSocket connection timeout, falling back to HTTP polling');
          ws.close();
          startHttpPolling();
        }
      }, 5000);

      ws.onopen = () => {
        clearTimeout(initialTimeout);
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'earthquake_data_update' || data.type === 'earthquake_update') {
            const earthquakeData = data.earthquakes || data.data || [];
            setEarthquakes(earthquakeData);
            
            // Generate PGA data from earthquake data
            const newPgaData = generatePGAData(earthquakeData);
            setPgaData(newPgaData);
            
            setLastUpdate(new Date());
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        clearTimeout(initialTimeout);
        console.log('WebSocket disconnected, falling back to HTTP polling');
        setConnectionStatus('disconnected');
        startHttpPolling();
      };

      ws.onerror = () => {
        clearTimeout(initialTimeout);
        console.log('WebSocket error, falling back to HTTP polling');
        setConnectionStatus('disconnected');
        startHttpPolling();
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnectionStatus('disconnected');
      startHttpPolling();
    }
  }, [startHttpPolling, generatePGAData]);

  useEffect(() => {
    setIsMounted(true);
    
    // Initial data fetch
    const fetchInitialData = async () => {
      try {
        const earthquakeResponse = await apiClient.get(API_ENDPOINTS.earthquake.recent);
        const earthquakeData = earthquakeResponse.slice(0, 50);
        setEarthquakes(earthquakeData);
        
        const newPgaData = generatePGAData(earthquakeData);
        setPgaData(newPgaData);
        
        setLastUpdate(new Date());
      } catch (err) {
        console.error('Failed to fetch initial data:', err);
      }
    };
    
    fetchInitialData();
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current);
      }
    };
  }, [connectWebSocket, generatePGAData]);

  if (!isMounted) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <div className="text-6xl mb-4">🗾</div>
          <div className="text-2xl font-bold">リアルタイム災害監視システム</div>
          <div className="text-lg mt-2">マップを読み込み中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen relative bg-gray-900 overflow-hidden">
      {/* Header Bar */}
      <div className="absolute top-0 left-0 right-0 z-[1000] bg-red-600 text-white px-6 py-3 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <div className="text-2xl">🚨</div>
          <h1 className="text-xl font-bold">リアルタイム災害監視システム</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm">
            {connectionStatus === 'connected' ? (
              <Badge className="bg-green-500 text-white animate-pulse">
                🔴 接続中
              </Badge>
            ) : (
              <Badge className="bg-gray-500 text-white">
                接続エラー
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Main Map */}
      <div className="h-full w-full pt-[60px]">
        <MapWithNoSSR
          earthquakes={earthquakes}
          pgaData={pgaData}
        />
      </div>

      {/* Last Update Overlay */}
      <div className="absolute top-[80px] left-4 z-[1000] bg-black/70 text-white px-4 py-2 rounded shadow-lg">
        <div className="text-xs">最終更新</div>
        <div className="text-lg font-mono">
          {lastUpdate.toLocaleTimeString('ja-JP')}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="absolute top-[80px] right-4 z-[1000] bg-red-600 text-white px-4 py-2 rounded shadow-lg">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
};

export default JapanMonitorMap;

