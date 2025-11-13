"use client";

import React, { useEffect, useState } from 'react';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';

interface EarthquakeEvent {
  id: string;
  time: string;
  location: string;
  magnitude: number;
  depth: number;
  latitude: number;
  longitude: number;
  intensity: string;
  tsunami: boolean;
}

interface ScrollingEarthquakeListProps {
  earthquakes?: EarthquakeEvent[];
  maxItems?: number;
  onSelect?: (earthquake: EarthquakeEvent) => void;
  showTestData?: boolean; // Optional: show test data if no real data available
}

const ScrollingEarthquakeList: React.FC<ScrollingEarthquakeListProps> = ({ 
  earthquakes: propEarthquakes,
  maxItems = 20,
  onSelect,
  showTestData = false
}) => {
  const [earthquakes, setEarthquakes] = useState<EarthquakeEvent[]>(propEarthquakes || []);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const handleSelect = (earthquake: EarthquakeEvent, index: number) => {
    setSelectedIndex(index);
    if (onSelect) {
      onSelect(earthquake);
    }
  };

  // Generate test earthquake data for demonstration
  const getTestEarthquakes = (): EarthquakeEvent[] => {
    const now = new Date();
    return [
      {
        id: 'test-1',
        time: new Date(now.getTime() - 10 * 60000).toISOString(),
        location: '奄美大島近海',
        magnitude: 2.7,
        depth: 20,
        latitude: 28.0,
        longitude: 129.5,
        intensity: '震度1',
        tsunami: false
      },
      {
        id: 'test-2',
        time: new Date(now.getTime() - 30 * 60000).toISOString(),
        location: '三陸沖',
        magnitude: 5.1,
        depth: 50,
        latitude: 39.5,
        longitude: 143.5,
        intensity: '震度2',
        tsunami: false
      },
      {
        id: 'test-3',
        time: new Date(now.getTime() - 60 * 60000).toISOString(),
        location: '千葉県東方沖',
        magnitude: 4.5,
        depth: 35,
        latitude: 35.5,
        longitude: 140.5,
        intensity: '震度3',
        tsunami: false
      },
      {
        id: 'test-4',
        time: new Date(now.getTime() - 120 * 60000).toISOString(),
        location: '和歌山県北部',
        magnitude: 3.2,
        depth: 10,
        latitude: 34.2,
        longitude: 135.2,
        intensity: '震度1',
        tsunami: false
      },
      {
        id: 'test-5',
        time: new Date(now.getTime() - 180 * 60000).toISOString(),
        location: '石川県能登地方',
        magnitude: 5.3,
        depth: 15,
        latitude: 37.5,
        longitude: 137.0,
        intensity: '震度3',
        tsunami: false
      }
    ];
  };

  useEffect(() => {
    if (!propEarthquakes) {
      // Fetch earthquake data if not provided
      const fetchEarthquakes = async () => {
        try {
          setIsLoading(true);
          const response = await apiClient.get(API_ENDPOINTS.p2p.latestEarthquakes);
          if (response.earthquakes && response.earthquakes.length > 0) {
            const formattedData = response.earthquakes.slice(0, maxItems).map((eq: any) => ({
              id: eq.id,
              time: eq.time,
              location: eq.location,
              magnitude: eq.magnitude || 0,
              depth: eq.depth || 0,
              latitude: eq.latitude || 0,
              longitude: eq.longitude || 0,
              intensity: eq.maxScaleString || '不明',
              tsunami: eq.tsunami || false
            }));
            setEarthquakes(formattedData);
            setIsLoading(false);
          } else if (showTestData) {
            // Show test data if enabled and no real data
            setEarthquakes(getTestEarthquakes());
            setIsLoading(false);
          } else {
            setIsLoading(false);
          }
        } catch (error) {
          console.error('Failed to fetch earthquakes:', error);
          // Use test data if fetch fails and showTestData is enabled
          if (showTestData) {
            setEarthquakes(getTestEarthquakes());
          }
          setIsLoading(false);
        }
      };

      fetchEarthquakes();
      const interval = setInterval(fetchEarthquakes, 30000); // Update every 30 seconds
      return () => clearInterval(interval);
    } else {
      setEarthquakes(propEarthquakes.slice(0, maxItems));
      setIsLoading(false);
    }
  }, [propEarthquakes, maxItems, showTestData]);

  const formatDate = (timeStr: string) => {
    try {
      const date = new Date(timeStr.replace(/\//g, '-'));
      const month = date.getMonth() + 1;
      const day = date.getDate();
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${month}月${day}日 ${hours}:${minutes}`;
    } catch {
      return timeStr;
    }
  };

  const getMagnitudeColor = (magnitude: number) => {
    if (magnitude >= 7.0) return 'bg-red-700';
    if (magnitude >= 6.0) return 'bg-red-600';
    if (magnitude >= 5.0) return 'bg-orange-500';
    if (magnitude >= 4.0) return 'bg-yellow-600';
    return 'bg-green-600';
  };

  const getIntensityColor = (intensity: string | number) => {
    const intensityStr = String(intensity);
    if (intensityStr.includes('7') || intensityStr === '震度7') return 'bg-purple-700 text-white';
    if (intensityStr.includes('6') || intensityStr === '震度6強' || intensityStr === '震度6弱') return 'bg-red-600 text-white';
    if (intensityStr.includes('5') || intensityStr === '震度5強' || intensityStr === '震度5弱') return 'bg-orange-500 text-white';
    if (intensityStr.includes('4') || intensityStr === '震度4') return 'bg-yellow-600 text-white';
    if (intensityStr.includes('3') || intensityStr === '震度3') return 'bg-yellow-500 text-black';
    if (intensityStr.includes('2') || intensityStr === '震度2') return 'bg-blue-500 text-white';
    if (intensityStr.includes('1') || intensityStr === '震度1') return 'bg-gray-600 text-white';
    return 'bg-gray-500 text-white';
  };

  const getIntensityDisplay = (intensity: string | number) => {
    const intensityStr = String(intensity);
    // Extract just the number for display
    if (intensityStr.includes('7')) return '7';
    if (intensityStr.includes('6')) return '6';
    if (intensityStr.includes('5')) return '5';
    if (intensityStr.includes('4')) return '4';
    if (intensityStr.includes('3')) return '3';
    if (intensityStr.includes('2')) return '2';
    if (intensityStr.includes('1')) return '1';
    return intensityStr;
  };

  return (
    <div className="h-full bg-[#0a1929] overflow-hidden relative">
      <style dangerouslySetInnerHTML={{
        __html: `
          .custom-scrollbar::-webkit-scrollbar {
            width: 8px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: #1e293b;
            border-radius: 4px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #3b82f6;
            border-radius: 4px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #60a5fa;
          }
          .custom-scrollbar {
            scrollbar-width: thin;
            scrollbar-color: #3b82f6 #1e293b;
          }
        `
      }} />
      <div className="h-full overflow-y-auto scroll-smooth custom-scrollbar">
        <div className="space-y-1 p-1 pb-12">
          {earthquakes.map((quake, index) => (
            <div
              key={quake.id}
              onClick={() => handleSelect(quake, index)}
              className={`p-2.5 cursor-pointer transition-all duration-150 border-l-2 ${
                selectedIndex === index 
                  ? 'bg-blue-900/40 border-blue-400 shadow-lg shadow-blue-900/50' 
                  : 'bg-[#132236] hover:bg-[#1a2d47] border-transparent hover:border-blue-800'
              }`}
            >
              <div className="flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  {/* Date and Time */}
                  <div className="text-gray-300 text-xs mb-1 font-mono">
                    {formatDate(quake.time)}ごろ
                  </div>
                  
                  {/* Location */}
                  <div className="text-white font-semibold text-sm mb-2 truncate">
                    {quake.location}
                  </div>
                  
                  {/* Magnitude and Details */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`px-2.5 py-1 rounded font-bold text-xs ${getMagnitudeColor(quake.magnitude)}`}>
                      M{quake.magnitude.toFixed(1)}
                    </span>
                    
                    {/* Intensity Box - Styled like the second image */}
                    <div className="flex items-center gap-1">
                      <span className={`w-7 h-7 flex items-center justify-center rounded font-bold text-sm ${getIntensityColor(quake.intensity)}`}>
                        {getIntensityDisplay(quake.intensity)}
                      </span>
                      <span className="text-gray-400 text-[10px]">
                        震度
                      </span>
                    </div>
                    
                    <span className="text-gray-400 text-[10px] ml-auto">
                      深さ {quake.depth}km
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {earthquakes.length === 0 && (
            <div className="text-center text-gray-400 py-12 px-4">
              <div className="text-4xl mb-3 opacity-30">📊</div>
              <div className="text-sm">地震情報はありません</div>
              <div className="text-xs text-gray-500 mt-2">
                データを取得中...
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Live indicator at the bottom */}
      {earthquakes.length > 0 && (
        <div className="absolute bottom-2 left-2 flex items-center gap-2 bg-red-600/90 px-3 py-1 rounded-full shadow-lg">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          <span className="text-white text-xs font-bold">ライブ</span>
        </div>
      )}
    </div>
  );
};

export default ScrollingEarthquakeList;

