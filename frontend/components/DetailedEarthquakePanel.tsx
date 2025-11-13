"use client";

import React from 'react';
import { Button } from '@/components/ui/button';

interface EarthquakeDetail {
  time: string;
  location: string;
  magnitude: number;
  depth: number;
  intensity: string;
  tsunami: boolean;
}

interface DetailedEarthquakePanelProps {
  earthquake?: EarthquakeDetail;
}

const DetailedEarthquakePanel: React.FC<DetailedEarthquakePanelProps> = ({ 
  earthquake 
}) => {
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

  const getIntensityColor = (intensity: string) => {
    const numIntensity = parseInt(intensity);
    if (numIntensity >= 6) return 'bg-red-600';
    if (numIntensity >= 5) return 'bg-orange-500';
    if (numIntensity >= 4) return 'bg-yellow-600';
    return 'bg-blue-600';
  };

  if (!earthquake) {
    return (
      <div className="h-full bg-[#0a1929] p-6 flex items-center justify-center">
        <div className="text-gray-500 text-center">
          <div className="text-4xl mb-2">🌍</div>
          <div>地震情報を選択してください</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-[#0a1929] overflow-y-auto scroll-smooth detail-panel p-6" style={{
      scrollbarWidth: 'thin',
      scrollbarColor: '#3b82f6 #1e293b'
    }}>
      <style dangerouslySetInnerHTML={{
        __html: `
          .detail-panel::-webkit-scrollbar {
            width: 8px;
          }
          .detail-panel::-webkit-scrollbar-track {
            background: #1e293b;
            border-radius: 4px;
          }
          .detail-panel::-webkit-scrollbar-thumb {
            background: #3b82f6;
            border-radius: 4px;
          }
          .detail-panel::-webkit-scrollbar-thumb:hover {
            background: #60a5fa;
          }
        `
      }} />
      <div className="space-y-4">
        {/* Maximum Intensity Display */}
        <div className={`${getIntensityColor(earthquake.intensity)} rounded-lg p-6 text-center`}>
          <div className="text-white text-sm mb-1">最大震度</div>
          <div className="text-white text-5xl font-bold">
            {earthquake.intensity}
          </div>
        </div>

        {/* Event Details */}
        <div className="bg-[#1a2942] rounded-lg p-6 text-white space-y-3">
          <div className="text-lg font-bold">
            {formatDate(earthquake.time)}ごろ
          </div>
          <div className="text-2xl font-bold text-blue-300">
            {earthquake.location}
          </div>
          <div className="text-base">
            で地震がありました
          </div>
        </div>

        {/* Magnitude and Depth */}
        <div className="bg-[#1a2942] rounded-lg p-6 text-white space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">マグニチュード</span>
            <span className="text-2xl font-bold text-yellow-400">
              {earthquake.magnitude.toFixed(1)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">深さ</span>
            <span className="text-xl font-bold">
              {earthquake.depth}km
            </span>
          </div>
        </div>

        {/* Tsunami Warning */}
        <div className="bg-[#1a2942] rounded-lg p-6 text-white">
          <div className="text-lg font-bold">
            {earthquake.tsunami ? (
              <span className="text-red-500">⚠️ 津波の可能性あり</span>
            ) : (
              <span className="text-green-500">✓ 津波の心配なし</span>
            )}
          </div>
        </div>

        {/* Action Button */}
        <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-6 text-lg">
          地震防災対策
        </Button>

        {/* Footer Logo */}
        <div className="text-center">
          <div className="text-gray-500 text-sm font-bold">
            Disaster Info System
          </div>
        </div>
      </div>
    </div>
  );
};

export default DetailedEarthquakePanel;

