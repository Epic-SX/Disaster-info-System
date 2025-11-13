'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Wifi, 
  WifiOff, 
  AlertTriangle, 
  MapPin, 
  Wind, 
  Waves,
  Radio,
  Activity,
  Camera
} from 'lucide-react';
import DisasterMap from './DisasterMap';
import WindDataDisplay from './WindDataDisplay';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';

interface LiveDashboardData {
  earthquakeCount: number;
  tsunamiCount: number;
  maxMagnitude: number;
  systemStatus: 'online' | 'offline' | 'warning';
  lastUpdate: Date;
}

const YouTubeLiveDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<LiveDashboardData>({
    earthquakeCount: 0,
    tsunamiCount: 0,
    maxMagnitude: 0,
    systemStatus: 'online',
    lastUpdate: new Date()
  });

  const [isLive, setIsLive] = useState(true);
  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // リアルタイム統計データの取得
  const fetchDashboardStats = async () => {
    try {
      const [earthquakeResponse, tsunamiResponse] = await Promise.allSettled([
        apiClient.get(API_ENDPOINTS.earthquake.recent),
        apiClient.get(API_ENDPOINTS.tsunami.alerts)
      ]);

      let earthquakeCount = 0;
      let maxMagnitude = 0;
      let tsunamiCount = 0;

      if (earthquakeResponse.status === 'fulfilled') {
        const earthquakes = earthquakeResponse.value || [];
        earthquakeCount = earthquakes.length;
        maxMagnitude = earthquakes.length > 0 ? 
          Math.max(...earthquakes.map((eq: any) => eq.magnitude || 0)) : 0;
      }

      if (tsunamiResponse.status === 'fulfilled') {
        const tsunamis = tsunamiResponse.value || [];
        tsunamiCount = tsunamis.length;
      }

      setDashboardData(prev => ({
        ...prev,
        earthquakeCount,
        tsunamiCount,
        maxMagnitude,
        systemStatus: 'online',
        lastUpdate: new Date()
      }));
    } catch (error) {
      console.error('統計データ取得エラー:', error);
      setDashboardData(prev => ({
        ...prev,
        systemStatus: 'warning',
        lastUpdate: new Date()
      }));
    }
  };

  useEffect(() => {
    // 初回データ取得
    fetchDashboardStats();

    // 30秒ごとに統計データを更新
    statsIntervalRef.current = setInterval(fetchDashboardStats, 30000);

    // 1秒ごとに更新時刻を更新
    const timeInterval = setInterval(() => {
      setDashboardData(prev => ({
        ...prev,
        lastUpdate: new Date()
      }));
    }, 1000);

    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
      clearInterval(timeInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-black text-white">
      {/* ライブ配信ヘッダー */}
      <div className="bg-gradient-to-r from-red-600 via-red-700 to-red-800 p-6 border-b border-red-500">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Radio className="h-8 w-8 text-white animate-pulse" />
                <div>
                  <h1 className="text-3xl font-bold">🚨 災害情報ライブ配信</h1>
                  <p className="text-red-100">24時間リアルタイム監視システム</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {isLive && (
                <Badge className="bg-red-600 text-white px-4 py-2 text-lg font-bold animate-pulse">
                  🔴 LIVE
                </Badge>
              )}
              <div className="text-right">
                <div className="text-sm text-red-100">現在時刻</div>
                <div className="text-xl font-mono font-bold">
                  {dashboardData.lastUpdate.toLocaleTimeString('ja-JP')}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* メインダッシュボード */}
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        
        {/* 緊急アラートバー */}
        <div className={`rounded-lg p-4 ${
          dashboardData.maxMagnitude >= 6.0 ? 
            'bg-gradient-to-r from-red-600 to-red-800 animate-pulse' :
          dashboardData.maxMagnitude >= 5.0 ?
            'bg-gradient-to-r from-orange-600 to-red-600' :
            'bg-gradient-to-r from-yellow-600 to-orange-600'
        }`}>
          <div className="flex items-center justify-center gap-4">
            <AlertTriangle className={`h-6 w-6 ${dashboardData.maxMagnitude >= 6.0 ? 'animate-bounce' : ''}`} />
            <div className="text-center">
              <div className="text-lg font-bold">
                {dashboardData.maxMagnitude >= 6.0 ? '🚨 大規模地震検出中' : '災害監視システム稼働中'}
              </div>
              <div className="text-sm">
                {dashboardData.maxMagnitude >= 6.0 ? 
                  `最大震度M${dashboardData.maxMagnitude.toFixed(1)} - 緊急警戒中` :
                  '地震・津波・気象情報をリアルタイム監視'
                }
              </div>
            </div>
            <div className="flex items-center gap-2">
              {dashboardData.systemStatus === 'online' ? (
                <Wifi className="h-5 w-5 text-green-400" />
              ) : (
                <WifiOff className="h-5 w-5 text-red-400" />
              )}
              <span className="text-sm">
                {dashboardData.systemStatus === 'online' ? '接続正常' : 'システム警告'}
              </span>
            </div>
          </div>
        </div>

        {/* 統計ダッシュボード */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-blue-600 to-blue-800 border-blue-500">
            <CardContent className="p-6 text-center text-white">
              <div className="text-4xl font-bold mb-2">{dashboardData.earthquakeCount}</div>
              <div className="text-blue-100">監視中の地震</div>
              <div className="text-xs text-blue-200 mt-1">過去24時間</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-600 to-red-600 border-orange-500">
            <CardContent className="p-6 text-center text-white">
              <div className="text-4xl font-bold mb-2">{dashboardData.tsunamiCount}</div>
              <div className="text-orange-100">津波警報</div>
              <div className="text-xs text-orange-200 mt-1">現在発令中</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-600 to-pink-600 border-purple-500">
            <CardContent className="p-6 text-center text-white">
              <div className="text-4xl font-bold mb-2">M{dashboardData.maxMagnitude.toFixed(1)}</div>
              <div className="text-purple-100">最大マグニチュード</div>
              <div className="text-xs text-purple-200 mt-1">過去24時間</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-600 to-emerald-600 border-green-500">
            <CardContent className="p-6 text-center text-white">
              <div className="text-4xl font-bold mb-2">
                {dashboardData.systemStatus === 'online' ? '100%' : '90%'}
              </div>
              <div className="text-green-100">システム稼働率</div>
              <div className="text-xs text-green-200 mt-1 flex items-center justify-center gap-1">
                <div className={`w-2 h-2 rounded-full animate-pulse ${
                  dashboardData.systemStatus === 'online' ? 'bg-green-400' : 'bg-yellow-400'
                }`}></div>
                {dashboardData.systemStatus === 'online' ? 'オンライン' : '部分稼働'}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* メインコンテンツエリア */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 災害マップ */}
          <div className="space-y-4">
            <DisasterMap />
          </div>

          {/* 風況データ */}
          <div className="space-y-4">
            <WindDataDisplay />
          </div>
        </div>

        {/* ライブカメラエリア（将来実装用） */}
        <Card className="bg-gradient-to-br from-gray-800 to-gray-900 border-gray-700">
          <CardContent className="p-6">
            <div className="text-center py-12">
              <Camera className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-2xl font-bold mb-2 text-white">ライブカメラフィード</h3>
              <p className="text-gray-400 mb-4">
                全国の災害監視カメラをリアルタイム配信
              </p>
              <Badge className="bg-yellow-600 text-white">
                次期アップデートで実装予定
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* フッター情報 */}
        <div className="bg-gray-800 rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-6 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              <span>P2P地震情報API</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              <span>気象庁データ</span>
            </div>
            <div className="flex items-center gap-2">
              <Wind className="h-4 w-4" />
              <span>リアルタイム気象観測</span>
            </div>
            <div className="flex items-center gap-2">
              <Waves className="h-4 w-4" />
              <span>津波監視システム</span>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            災害情報システム v2.0 - 24時間365日監視中
          </div>
        </div>
      </div>
    </div>
  );
};

export default YouTubeLiveDashboard; 