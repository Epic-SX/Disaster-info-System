"use client";

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import DigitalClock from './DigitalClock';
import ScrollingEarthquakeList from './ScrollingEarthquakeList';
import DetailedEarthquakePanel from './DetailedEarthquakePanel';
import WindSpeedPanel from './WindSpeedPanel';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';

// Dynamically import components to avoid SSR issues
const SeismicWaveformDisplay = dynamic(() => import('./SeismicWaveformDisplay'), {
  ssr: false,
  loading: () => <div className="h-full bg-black flex items-center justify-center text-white">Loading waveforms...</div>
});

const SeismicStationMapComponent = dynamic(() => import('./SeismicStationMapComponent'), {
  ssr: false,
  loading: () => <div className="h-full bg-[#0a1929] flex items-center justify-center text-white">Loading map...</div>
});

const DetailedEarthquakeMap = dynamic(() => import('./DetailedEarthquakeMap'), {
  ssr: false,
  loading: () => <div className="h-full bg-[#0a1929] flex items-center justify-center text-white">Loading map...</div>
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
  const [vibrationLevel, setVibrationLevel] = useState<number>(0);

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

  // Simulate vibration level changes
  useEffect(() => {
    const updateVibration = () => {
      const newLevel = Math.floor(Math.random() * 3); // 0-2
      setVibrationLevel(newLevel);
    };

    const interval = setInterval(updateVibration, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleEarthquakeSelect = (earthquake: EarthquakeData) => {
    setSelectedEarthquake(earthquake);
  };

  return (
    <div className="h-screen w-screen bg-[#0a0e1a] text-white overflow-hidden flex flex-col">
      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-12 gap-0.5 bg-gray-900">
        {/* Left Column - Seismic Station Map */}
        <div className="col-span-3 bg-[#0a1929] flex flex-col">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700">
            <div className="text-lg font-bold text-white">地中 NEW teeFive</div>
            <div className="text-xs text-gray-400">{currentTime}</div>
          </div>
          <div className="flex-1 relative">
            <SeismicStationMapComponent />
          </div>
        </div>

        {/* Middle Column - Seismic Waveforms */}
        <div className="col-span-6 bg-black flex flex-col">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700">
            <div className="text-lg font-bold text-white">地震波形モニター</div>
            <div className="text-xs text-gray-400">リアルタイム波形表示</div>
          </div>
          <div className="flex-1">
            <SeismicWaveformDisplay />
          </div>
        </div>

        {/* Right Column - Clock & Local Map */}
        <div className="col-span-3 bg-[#0a1929] flex flex-col">
          {/* Digital Clock */}
          <div className="bg-[#1a2942] p-6 text-center border-b border-gray-700">
            <DigitalClock className="text-6xl text-green-400" />
            <div className="mt-4">
              <div className="text-sm text-gray-400">振動</div>
              <div className="text-2xl font-bold text-white">
                レベル {vibrationLevel}
              </div>
            </div>
            <div className="mt-4 bg-yellow-500/20 border border-yellow-500 rounded p-2">
              <div className="text-xs text-yellow-300 font-bold">
                ⭐ 防災ブランド Bunker
              </div>
            </div>
            <div className="mt-2 text-sm text-gray-300">
              この地震による津波の心配はなし
            </div>
          </div>

          {/* Detailed Earthquake Map */}
          <div className="flex-1 bg-[#0a1929] flex flex-col">
            <div className="bg-[#1a2942] p-3 border-b border-gray-700">
              <div className="text-sm font-bold text-white">震源詳細マップ</div>
              <div className="text-xs text-gray-400">Epicenter Detail Map</div>
            </div>
            <div className="flex-1">
              <DetailedEarthquakeMap earthquake={selectedEarthquake || undefined} />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="h-[40vh] grid grid-cols-12 gap-0.5 bg-gray-900">
        {/* Earthquake List */}
        <div className="col-span-3 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <div className="bg-[#1a2942] p-3 border-b border-gray-700">
            <div className="text-base font-bold text-white">最近の地震活動</div>
          </div>
          <div className="flex-1 min-h-0">
            <ScrollingEarthquakeList 
              earthquakes={earthquakes}
              maxItems={20}
              onSelect={handleEarthquakeSelect}
              showTestData={false}
            />
          </div>
        </div>

        {/* Detailed Earthquake Info */}
        <div className="col-span-7 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <DetailedEarthquakePanel 
            earthquake={selectedEarthquake || undefined}
          />
        </div>

        {/* Wind Speed Panel */}
        <div className="col-span-2 bg-[#0a1929] flex flex-col min-h-0 overflow-hidden">
          <WindSpeedPanel />
        </div>
      </div>
    </div>
  );
};

export default TechnicalMonitorDashboard;

