"use client";

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import DetailedEarthquakePanel from './DetailedEarthquakePanel';
import YouTubeLiveNewsList from './YouTubeLiveNewsList';
import AMeDASInteractiveMapWithJapan from './AMeDASInteractiveMapWithJapan';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';

// Dynamically import components to avoid SSR issues
const SeismicStationMapComponent = dynamic(() => import('./SeismicStationMapComponent'), {
  ssr: false,
  loading: () => <div className="h-full bg-[#0a1929] flex items-center justify-center text-white">Loading map...</div>
});

const DetailedEarthquakeMap = dynamic(() => import('./DetailedEarthquakeMap'), {
  ssr: false,
  loading: () => <div className="h-full bg-[#0a1929] flex items-center justify-center text-white">Loading map...</div>
});

const CoastGuardCameraPanel = dynamic(() => import('./CoastGuardCameraPanel'), {
  ssr: false,
  loading: () => <div className="h-full bg-black flex items-center justify-center text-white">Loading live cameras...</div>
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
  maxScale?: number;  // Numeric intensity value for sorting
  tsunami: boolean;
}

interface PGADataPoint {
  id: string;
  latitude: number;
  longitude: number;
  pga: number;
  location: string;
}

const TechnicalMonitorDashboard: React.FC = () => {
  const [selectedEarthquake, setSelectedEarthquake] = useState<EarthquakeData | null>(null);
  const [earthquakes, setEarthquakes] = useState<EarthquakeData[]>([]);
  const [pgaData, setPGAData] = useState<PGADataPoint[]>([]);
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Fetch earthquake data
    const fetchData = async () => {
      try {
        const response = await apiClient.get(API_ENDPOINTS.p2p.latestEarthquakes);
        console.log('API Response:', response);
        
        if (response && response.earthquakes && Array.isArray(response.earthquakes)) {
          const formattedData = response.earthquakes.map((eq: any) => ({
            id: eq.id || `eq-${Date.now()}-${Math.random()}`,
            time: eq.time || new Date().toISOString(),
            location: eq.location || '不明',
            magnitude: eq.magnitude || 0,
            depth: eq.depth || 0,
            latitude: eq.latitude || 0,
            longitude: eq.longitude || 0,
            intensity: eq.maxScaleString || '不明',
            maxScale: eq.maxScale || 0,
            tsunami: eq.tsunami || false
          }));
          
          console.log('Formatted earthquake data:', formattedData);
          setEarthquakes(formattedData);
          
          // Find and set the strongest earthquake (highest intensity or magnitude)
          if (formattedData.length > 0) {
            // Sort by maxScale (intensity) first, then by magnitude
            const sortedByStrength = [...formattedData].sort((a, b) => {
              // Compare by intensity first
              const scaleA = a.maxScale || 0;
              const scaleB = b.maxScale || 0;
              if (scaleA !== scaleB) return scaleB - scaleA;
              
              // If intensity is the same, compare by magnitude
              return (b.magnitude || 0) - (a.magnitude || 0);
            });
            
            // Select the strongest earthquake
            const strongestEarthquake = sortedByStrength[0];
            setSelectedEarthquake(strongestEarthquake);
            console.log('Strongest earthquake selected:', strongestEarthquake);
          }

          // Generate PGA data from earthquakes
          const pga = formattedData.map((eq: any) => ({
            id: eq.id,
            latitude: eq.latitude,
            longitude: eq.longitude,
            pga: (eq.magnitude || 0) * 30 + Math.random() * 50, // Simulate PGA values
            location: eq.location
          }));
          setPGAData(pga);
        } else {
          console.log('No earthquake data available in response');
          setEarthquakes([]);
        }
      } catch (error) {
        console.error('Failed to fetch earthquake data:', error);
        // Set empty state on error to prevent component crash
        setEarthquakes([]);
        setPGAData([]);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Update current time
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      const day = now.getDate();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      setCurrentTime(`${year}/${month}/${day} ${hours}:${minutes}:${seconds}`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleEarthquakeSelect = (earthquake: EarthquakeData) => {
    setSelectedEarthquake(earthquake);
  };

  return (
    <div className="h-full w-full bg-[#050914] text-white overflow-hidden flex flex-col">
      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-0.5 bg-gray-900 min-h-0" style={{ flex: '0 0 55%' }}>
        {/* Left Column - Seismic Station Map */}
        <div className="col-span-4 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700 flex-shrink-0">
            <div className="text-lg font-bold text-white">地中 NEW teeFive</div>
            <div className="text-xs text-gray-400">{currentTime}</div>
          </div>
          <div className="flex-1 relative min-h-0 overflow-hidden">
            <SeismicStationMapComponent />
          </div>
        </div>

        {/* Middle Column - Coastal Camera & Tsunami Monitor */}
        <div className="col-span-8 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <CoastGuardCameraPanel />
        </div>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-12 gap-0.5 bg-gray-900 min-h-0" style={{ flex: '0 0 45%' }}>
        {/* Disaster News Articles */}
        <div className="col-span-3 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <YouTubeLiveNewsList className="h-full rounded-none border-0" />
        </div>

        {/* Detailed Earthquake Info */}
        <div className="col-span-3 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700 flex-shrink-0">
            <div className="text-base font-bold text-white">最大震度 / 詳細情報</div>
            <div className="text-xs text-gray-400">Detailed earthquake status</div>
          </div>
          <div className="flex-1 overflow-hidden min-h-0">
            <DetailedEarthquakePanel 
              earthquake={selectedEarthquake || undefined}
            />
          </div>
        </div>

        {/* Epicenter Detail Map */}
        <div className="col-span-2 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700 flex-shrink-0">
            <div className="text-base font-bold text-white">震源詳細マップ</div>
            <div className="text-xs text-gray-400">Epicenter Detail Map</div>
          </div>
          <div className="flex-1 min-h-0 overflow-hidden">
            <DetailedEarthquakeMap earthquake={selectedEarthquake || undefined} />
          </div>
        </div>

        {/* Wind Map */}
        <div className="col-span-4 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700 flex-shrink-0">
            <div className="text-base font-bold text-white">風況マップ</div>
            <div className="text-xs text-gray-400">リアルタイム風向・風速</div>
          </div>
          <div className="flex-1 overflow-hidden min-h-0">
            <AMeDASInteractiveMapWithJapan showDetails={false} mapHeight="100%" className="h-full bg-transparent border-none" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TechnicalMonitorDashboard;

