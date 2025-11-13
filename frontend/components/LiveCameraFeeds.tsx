import React, { useState, useEffect, useMemo } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useWebSocket } from '../hooks/useWebSocket';
import { getWebSocketConfig } from '../config/websocket';

interface CameraFeed {
  id: string;
  name: string;
  status: string;
  location: string;
  stream_url?: string;
  thumbnail_url?: string;
  last_updated: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

const LiveCameraFeeds: React.FC = () => {
  const [cameraFeeds, setCameraFeeds] = useState<CameraFeed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Memoize WebSocket configuration to prevent unnecessary re-renders
  const wsConfig = useMemo(() => getWebSocketConfig(), []);

  // WebSocket connection for real-time updates
  const { isConnected, error: wsError, isDisabled } = useWebSocket({
    url: wsConfig.url,
    fallbackUrls: wsConfig.fallbackUrls,
    onMessage: (message) => {
      console.log('WebSocket message received in LiveCameraFeeds:', message);
      if (message.type === 'camera_feeds_update') {
        setCameraFeeds(message.data || []);
        setLoading(false);
        setError(null);
      }
    },
    onOpen: () => {
      console.log('WebSocket connected for camera feeds updates');
    },
    onClose: () => {
      console.log('WebSocket disconnected for camera feeds updates');
    },
    onError: (error) => {
      console.error('WebSocket error for camera feeds updates:', error);
    }
  });

  useEffect(() => {
    const fetchCameraFeeds = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/camera-feeds');
        if (!response.ok) {
          throw new Error('Failed to fetch camera feeds');
        }
        const data = await response.json();
        setCameraFeeds(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        console.error('Error fetching camera feeds:', err);
      } finally {
        setLoading(false);
      }
    };

    // Only fetch initially if WebSocket is not connected
    if (!isConnected) {
      fetchCameraFeeds();
    }
    
    // Fallback: refresh camera feeds every 2 minutes if WebSocket fails
    const interval = setInterval(fetchCameraFeeds, 2 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [isConnected]);

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'online': return 'オンライン';
      case 'maintenance': return 'メンテナンス中';
      case 'offline': return 'オフライン';
      default: return status;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'online': return 'default';
      case 'maintenance': return 'secondary';
      case 'offline': return 'destructive';
      default: return 'outline';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return '📹';
      case 'maintenance': return '🔧';
      case 'offline': return '❌';
      default: return '❓';
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">📹 ライブカメラ映像</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="border rounded-lg p-3 animate-pulse">
                <div className="flex justify-between items-center mb-2">
                  <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                  <div className="h-6 bg-gray-200 rounded w-20"></div>
                </div>
                <div className="bg-gray-200 h-32 rounded mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">📹 ライブカメラ映像</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-red-500 mb-2">エラーが発生しました</p>
            <p className="text-sm text-gray-600">{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              再読み込み
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="text-xl font-bold">📹 ライブカメラ映像</CardTitle>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              isDisabled ? 'bg-gray-500' : 
              isConnected ? 'bg-green-500' : 
              wsError ? 'bg-red-500' : 'bg-yellow-500'
            }`}></div>
            <span className="text-xs text-gray-500">
              {isDisabled ? '無効' : 
               isConnected ? 'リアルタイム' : 
               wsError ? 'エラー' : '接続中'}
            </span>
            {wsError && (
              <span className="text-xs text-red-500 ml-1" title={wsError}>
                ⚠️
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {cameraFeeds.length === 0 ? (
            <div className="col-span-2 text-center py-8 text-gray-500">
              カメラフィードがありません
            </div>
          ) : (
            cameraFeeds.map((feed) => (
              <div key={feed.id} className="border rounded-lg p-3">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold">{feed.name}</h3>
                  <Badge variant={getStatusVariant(feed.status) as any}>
                    {getStatusLabel(feed.status)}
                  </Badge>
                </div>
                <div className="bg-gray-200 h-32 rounded flex items-center justify-center mb-2 relative overflow-hidden">
                  {feed.thumbnail_url && feed.status === 'online' ? (
                    <Image 
                      src={feed.thumbnail_url} 
                      alt={`${feed.name} thumbnail`}
                      fill
                      className="object-cover"
                      onError={(e) => {
                        const target = e.currentTarget as HTMLImageElement;
                        const parent = target.parentElement;
                        if (parent) {
                          const fallback = parent.querySelector('.fallback-content') as HTMLElement;
                          if (fallback) {
                            target.style.display = 'none';
                            fallback.style.display = 'flex';
                          }
                        }
                      }}
                    />
                  ) : null}
                  <div 
                    className={`fallback-content absolute inset-0 flex items-center justify-center rounded ${
                      feed.thumbnail_url && feed.status === 'online' ? 'hidden' : 'flex'
                    }`}
                  >
                    <span className="text-2xl">
                      {getStatusIcon(feed.status)}
                    </span>
                    <span className="ml-2">
                      {feed.status === 'online' ? 'ライブ映像' : 
                       feed.status === 'maintenance' ? 'メンテナンス中' : 'オフライン'}
                    </span>
                  </div>
                </div>
                <div className="text-sm text-gray-600">{feed.location}</div>
                {feed.stream_url && feed.status === 'online' && (
                  <button 
                    className="mt-2 w-full px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                    onClick={() => window.open(feed.stream_url, '_blank')}
                  >
                    ライブ映像を見る
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default LiveCameraFeeds; 