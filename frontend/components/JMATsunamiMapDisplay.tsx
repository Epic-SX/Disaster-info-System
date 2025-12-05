"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import dynamic from 'next/dynamic';
import { apiRequest, API_ENDPOINTS } from '@/lib/api-config';
import { RefreshCw, AlertTriangle } from 'lucide-react';

// Dynamically import the entire map component to avoid SSR issues
const MapWithNoSSR = dynamic(
  () => import('./JMATsunamiMapInner'),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full w-full flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="text-4xl mb-2">🗾</div>
          <div className="text-sm text-gray-600">マップを読み込み中...</div>
        </div>
      </div>
    )
  }
);

interface JMATsunamiStatus {
  message: string;
  has_warning: boolean;
  warning_type: string | null;
  affected_areas: string[];
  timestamp: string | null;
  source: string;
}

const JMATsunamiMapDisplay: React.FC = () => {
  const [jmaStatus, setJmaStatus] = useState<JMATsunamiStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    fetchJmaStatus();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchJmaStatus, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchJmaStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<JMATsunamiStatus>(API_ENDPOINTS.tsunami.jmaStatus);
      if (data && data.message) {
        setJmaStatus(data);
      } else {
        console.error('Invalid data received:', data);
        setError('データの取得に失敗しました。サーバーを確認してください。');
      }
    } catch (err) {
      console.error('Error fetching JMA tsunami status:', err);
      setError(`データの取得に失敗しました: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return null;
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return null;
    }
  };

  if (!isMounted) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-xl font-bold">🌊 津波情報マップ</CardTitle>
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
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span>🌊 津波情報マップ (JMA)</span>
          <button
            onClick={fetchJmaStatus}
            disabled={loading}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="更新"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="relative h-[500px] w-full rounded-lg overflow-hidden border">
          {isMounted && <MapWithNoSSR />}

          {/* White text box overlay - matching JMA website style */}
          <div className="absolute top-8 left-8 z-[1000] max-w-lg">
            <div 
              className="bg-white rounded-lg shadow-md p-5"
              style={{
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
                backgroundColor: '#ffffff'
              }}
            >
              {loading ? (
                <div className="flex items-center gap-2 text-gray-600">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">読み込み中...</span>
                </div>
              ) : error ? (
                <div className="flex items-center gap-2 text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">{error}</span>
                </div>
              ) : jmaStatus ? (
                <div className="text-sm text-gray-900 leading-relaxed whitespace-normal">
                  {jmaStatus.message}
                </div>
              ) : (
                <div className="text-sm text-gray-600">
                  データが利用できません
                </div>
              )}
            </div>
          </div>

          {/* Warning indicator in top right if warning exists */}
          {jmaStatus?.has_warning && jmaStatus.warning_type && (
            <div className="absolute top-4 right-4 z-[1000]">
              <div 
                className={`px-4 py-2 rounded-lg text-white font-bold shadow-lg ${
                  jmaStatus.warning_type === '大津波警報' 
                    ? 'bg-red-600 animate-pulse' 
                    : jmaStatus.warning_type === '津波警報'
                    ? 'bg-red-500'
                    : 'bg-yellow-500'
                }`}
              >
                {jmaStatus.warning_type}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default JMATsunamiMapDisplay;

