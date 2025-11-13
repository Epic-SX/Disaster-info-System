"use client";

import React, { useEffect, useState } from 'react';
import { Wind } from 'lucide-react';

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

const WindSpeedPanel: React.FC = () => {
  const [windData, setWindData] = useState<WindData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchWindData = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/weather/wind`);
        if (response.ok) {
          const data = await response.json();
          // Limit to first 10 stations for the panel
          setWindData(data.slice(0, 10));
          setError('');
        } else {
          setError('風況データの取得に失敗しました');
        }
        setLoading(false);
      } catch (err) {
        console.error('Error fetching wind data:', err);
        setError('データ取得エラー');
        setLoading(false);
      }
    };

    fetchWindData();
    const interval = setInterval(fetchWindData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'error': return 'text-red-500';
      case 'moderate': return 'text-yellow-500';
      case 'calm': return 'text-green-500';
      default: return 'text-blue-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'error': return '🔴';
      case 'moderate': return '🟡';
      case 'calm': return '🟢';
      default: return '🔵';
    }
  };

  if (loading) {
    return (
      <div className="h-full bg-[#0a1929] flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="h-full bg-[#0a1929] flex flex-col">
      <style dangerouslySetInnerHTML={{
        __html: `
          .wind-panel-scroll::-webkit-scrollbar {
            width: 8px;
          }
          .wind-panel-scroll::-webkit-scrollbar-track {
            background: #1e293b;
            border-radius: 4px;
          }
          .wind-panel-scroll::-webkit-scrollbar-thumb {
            background: #3b82f6;
            border-radius: 4px;
          }
          .wind-panel-scroll::-webkit-scrollbar-thumb:hover {
            background: #60a5fa;
          }
          .wind-panel-scroll {
            scrollbar-width: thin;
            scrollbar-color: #3b82f6 #1e293b;
          }
        `
      }} />
      {/* Header */}
      <div className="bg-[#1a2942] p-3 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Wind className="h-5 w-5 text-blue-400" />
          <div className="text-base font-bold text-white">風速情報</div>
        </div>
        <div className="text-xs text-gray-400 mt-1">リアルタイム観測データ</div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto scroll-smooth wind-panel-scroll">
        {error ? (
          <div className="p-4 text-center text-red-500">{error}</div>
        ) : (
          <div className="p-3 space-y-2">
            {windData.map((data, index) => (
              <div 
                key={index}
                className="bg-[#1a2942] rounded-lg p-3 hover:bg-[#243854] transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getStatusIcon(data.status)}</span>
                    <span className="text-white font-bold text-sm">{data.location}</span>
                  </div>
                  <span className={`text-xs font-mono ${getStatusColor(data.status)}`}>
                    {data.status.toUpperCase()}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">風速:</span>
                    <span className="text-white font-bold">{data.speed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">方向:</span>
                    <span className="text-white">{data.direction}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">最大瞬間:</span>
                    <span className="text-yellow-400 font-bold">{data.gusts}</span>
                  </div>
                  {data.temperature && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">気温:</span>
                      <span className="text-blue-300">{data.temperature}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="bg-[#1a2942] p-3 border-t border-gray-700">
        <div className="flex justify-between items-center text-xs">
          <div className="text-gray-400">
            観測地点: <span className="text-white font-bold">{windData.length}</span>
          </div>
          <div className="text-gray-400">
            最高風速: <span className="text-yellow-400 font-bold">
              {windData.length > 0 ? Math.max(...windData.map(d => parseFloat(d.speed))).toFixed(1) : '0'} km/h
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WindSpeedPanel;

