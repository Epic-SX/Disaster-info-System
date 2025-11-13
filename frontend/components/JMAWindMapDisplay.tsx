'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wind, MapPin, AlertTriangle, RefreshCw } from 'lucide-react'

interface WindLocation {
  location: string;
  wind_speed: number;
  wind_direction: string;
  observation_time: string;
  lat?: number;
  lon?: number;
}

interface WindSummary {
  status: string;
  observation_time?: string;
  total_stations: number;
  average_wind_speed: number;
  max_wind_speed: number;
  max_wind_location: string;
  max_wind_direction: string;
  alert_level: string;
  alert_color: string;
  top_10_windy_locations: WindLocation[];
}

const JMAWindMapDisplay: React.FC = () => {
  const [windSummary, setWindSummary] = useState<WindSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  const fetchWindData = React.useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/weather/wind/summary`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'ok') {
          setWindSummary(data);
          setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
          setError('');
        } else {
          setError(data.message || '風況データが取得できません');
        }
      } else {
        setError('風況データの取得に失敗しました');
      }
      setLoading(false);
    } catch (err) {
      console.error('Error fetching wind data:', err);
      setError('データ取得エラー');
      setLoading(false);
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    // Initial fetch
    fetchWindData();

    // Auto-refresh every 10 minutes (600000ms)
    refreshIntervalRef.current = setInterval(() => {
      fetchWindData();
    }, 600000);

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [fetchWindData]);

  const getAlertBadgeColor = (alertColor: string) => {
    switch (alertColor) {
      case 'red':
        return 'bg-red-600 text-white animate-pulse';
      case 'orange':
        return 'bg-orange-600 text-white';
      case 'green':
        return 'bg-green-600 text-white';
      case 'blue':
        return 'bg-blue-600 text-white';
      default:
        return 'bg-gray-600 text-white';
    }
  };

  const getWindDirectionArrow = (direction: string) => {
    const directionMap: Record<string, string> = {
      '北': '↓',
      '北北東': '↙',
      '北東': '↙',
      '東北東': '↙',
      '東': '←',
      '東南東': '↖',
      '南東': '↖',
      '南南東': '↖',
      '南': '↑',
      '南南西': '↗',
      '南西': '↗',
      '西南西': '↗',
      '西': '→',
      '西北西': '↘',
      '北西': '↘',
      '北北西': '↘',
    };
    return directionMap[direction] || '•';
  };

  const handleManualRefresh = () => {
    setLoading(true);
    fetchWindData();
  };

  if (loading && !windSummary) {
    return (
      <Card className="bg-gradient-to-br from-blue-900 to-indigo-900 text-white border-blue-700">
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <Wind className="h-6 w-6 animate-spin" />
            🌬️ JMA 風況マップ
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="animate-spin text-5xl mb-4">🌪️</div>
            <p className="text-blue-200 text-lg font-medium">風況データを読み込み中...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !windSummary) {
    return (
      <Card className="bg-gradient-to-br from-red-900 to-orange-900 text-white border-red-700">
        <CardHeader>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <AlertTriangle className="h-6 w-6" />
            🌬️ JMA 風況マップ
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="text-5xl mb-4">⚠️</div>
            <p className="text-red-200 text-lg font-medium">{error}</p>
            <button 
              onClick={handleManualRefresh}
              className="mt-4 px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-bold transition-colors"
            >
              <RefreshCw className="h-4 w-4 inline mr-2" />
              再試行
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-blue-900 to-indigo-900 text-white border-blue-700 shadow-2xl">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600">
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wind className="h-6 w-6" />
            🌬️ JMA 風況マップ
          </span>
          <div className="flex items-center gap-3">
            {windSummary && (
              <Badge className={getAlertBadgeColor(windSummary.alert_color)}>
                {windSummary.alert_level}
              </Badge>
            )}
            <button 
              onClick={handleManualRefresh}
              className="p-2 hover:bg-blue-700 rounded-lg transition-colors"
              title="データを更新"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </CardTitle>
        {lastUpdate && (
          <div className="text-xs text-blue-100 mt-1">
            最終更新: {lastUpdate} | データソース: 気象庁アメダス
          </div>
        )}
      </CardHeader>
      <CardContent className="p-6">
        {windSummary && (
          <div className="space-y-6">
            {/* 警戒レベル表示 */}
            {windSummary.alert_color === 'red' || windSummary.alert_color === 'orange' ? (
              <div className={`p-4 rounded-lg text-center font-bold text-lg ${
                windSummary.alert_color === 'red' 
                  ? 'bg-red-600 animate-pulse' 
                  : 'bg-orange-600'
              }`}>
                <AlertTriangle className="h-6 w-6 inline mr-2" />
                {windSummary.alert_level}
              </div>
            ) : null}

            {/* 全体統計 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gradient-to-br from-blue-700 to-blue-800 rounded-lg p-4 text-center">
                <div className="text-sm text-blue-200 mb-1">監視地点</div>
                <div className="text-3xl font-bold">{windSummary.total_stations}</div>
                <div className="text-xs text-blue-300 mt-1">地点</div>
              </div>
              
              <div className="bg-gradient-to-br from-green-700 to-green-800 rounded-lg p-4 text-center">
                <div className="text-sm text-green-200 mb-1">平均風速</div>
                <div className="text-3xl font-bold">{windSummary.average_wind_speed}</div>
                <div className="text-xs text-green-300 mt-1">m/s</div>
              </div>
              
              <div className="bg-gradient-to-br from-orange-700 to-red-800 rounded-lg p-4 text-center">
                <div className="text-sm text-orange-200 mb-1">最大風速</div>
                <div className="text-3xl font-bold">{windSummary.max_wind_speed}</div>
                <div className="text-xs text-orange-300 mt-1">m/s</div>
              </div>
              
              <div className="bg-gradient-to-br from-purple-700 to-pink-800 rounded-lg p-4 text-center">
                <div className="text-sm text-purple-200 mb-1">最大地点</div>
                <div className="text-lg font-bold truncate">{windSummary.max_wind_location}</div>
                <div className="text-xs text-purple-300 mt-1">
                  {windSummary.max_wind_direction} {getWindDirectionArrow(windSummary.max_wind_direction)}
                </div>
              </div>
            </div>

            {/* 風速トップ10地点 */}
            <div>
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                風速トップ10地点
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {windSummary.top_10_windy_locations.map((location, index) => (
                  <div
                    key={`${location.location}-${index}`}
                    className={`p-3 rounded-lg border-2 transition-all duration-300 ${
                      location.wind_speed >= 15
                        ? 'bg-red-900/50 border-red-500'
                        : location.wind_speed >= 10
                        ? 'bg-orange-900/50 border-orange-500'
                        : 'bg-blue-900/50 border-blue-500'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold text-blue-300">
                          {index + 1}
                        </span>
                        <div>
                          <div className="font-bold text-white">{location.location}</div>
                          <div className="text-xs text-blue-200">
                            {location.wind_direction} {getWindDirectionArrow(location.wind_direction)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-cyan-300">
                          {location.wind_speed}
                        </div>
                        <div className="text-xs text-blue-200">m/s</div>
                      </div>
                    </div>
                    {location.wind_speed >= 15 && (
                      <div className="mt-2 text-xs text-red-200 font-bold">
                        ⚠️ 強風警戒
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* 風速基準説明 */}
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-bold mb-2 text-sm">風速の目安</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded"></div>
                  <span>0-5 m/s: 穏やか</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded"></div>
                  <span>5-10 m/s: 通常</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-orange-500 rounded"></div>
                  <span>10-15 m/s: やや強い</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded animate-pulse"></div>
                  <span>15+ m/s: 強風警戒</span>
                </div>
              </div>
            </div>

            {/* JMA リンク */}
            <div className="text-center pt-4 border-t border-blue-700">
              <a 
                href="https://www.jma.go.jp/bosai/map.html#8/35.673/139.697/&elem=wind&contents=amedas&interval=60"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-300 hover:text-blue-100 transition-colors text-sm"
              >
                <MapPin className="h-4 w-4" />
                気象庁 風況マップで詳細を見る →
              </a>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default JMAWindMapDisplay;

