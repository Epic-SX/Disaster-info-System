import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '../hooks/useWebSocket';
import { getWebSocketConfig } from '../config/websocket';

interface SocialMediaChannel {
  channel_id: string;
  channel_name: string;
  platform: string;
  is_active: boolean;
  auto_posting: boolean;
  auto_commenting: boolean;
  posting_frequency: number;
  commenting_frequency: number;
  disaster_types: string[];
  language: string;
}

interface SocialMediaStatus {
  total_channels: number;
  active_channels: number;
  platforms: Record<string, number>;
  recent_posts: number;
  total_posts_today: number;
  ai_service_available: boolean;
  recurring_jobs: number;
}

const SocialMediaDashboard: React.FC = () => {
  const [channels, setChannels] = useState<SocialMediaChannel[]>([]);
  const [status, setStatus] = useState<SocialMediaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Memoize WebSocket configuration to prevent unnecessary re-renders
  const wsConfig = useMemo(() => getWebSocketConfig(), []);

  // WebSocket connection for real-time updates
  const { isConnected } = useWebSocket({
    url: wsConfig.url,
    fallbackUrls: wsConfig.fallbackUrls,
    onMessage: (message) => {
      if (message.type === 'social_media_update') {
        // Refresh data when social media updates are received
        fetchSocialMediaData();
      }
    },
    onOpen: () => {
      console.log('WebSocket connected for social media updates');
    },
    onClose: () => {
      console.log('WebSocket disconnected for social media updates');
    },
    onError: (error) => {
      console.error('WebSocket error for social media updates:', error);
    }
  });

  const fetchSocialMediaData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch channels and status in parallel
      const [channelsResponse, statusResponse] = await Promise.all([
        fetch('/api/social-media/channels'),
        fetch('/api/social-media/status')
      ]);

      if (!channelsResponse.ok || !statusResponse.ok) {
        throw new Error('Failed to fetch social media data');
      }

      const channelsData = await channelsResponse.json();
      const statusData = await statusResponse.json();

      setChannels(channelsData.channels || []);
      setStatus(statusData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error fetching social media data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Only fetch initially if WebSocket is not connected
    if (!isConnected) {
      fetchSocialMediaData();
    }
    
    // Fallback: refresh data every 5 minutes if WebSocket fails
    const interval = setInterval(fetchSocialMediaData, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [isConnected]);

  const getStatusLabel = (isActive: boolean, autoPosting: boolean) => {
    if (isActive && autoPosting) return 'アクティブ';
    if (isActive && !autoPosting) return '手動モード';
    return '非アクティブ';
  };

  const getStatusVariant = (isActive: boolean, autoPosting: boolean) => {
    if (isActive && autoPosting) return 'default';
    if (isActive && !autoPosting) return 'secondary';
    return 'destructive';
  };

  const getPlatformDisplayName = (platform: string) => {
    const platformNames: Record<string, string> = {
      'line': 'LINE',
      'youtube_live': 'YouTube Live',
      'tiktok': 'TikTok',
      'yahoo': 'Yahoo!',
      'twitter': 'Twitter',
      'facebook': 'Facebook',
      'instagram': 'Instagram'
    };
    return platformNames[platform] || platform;
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      'line': '💬',
      'youtube_live': '📺',
      'tiktok': '🎵',
      'yahoo': '🔍',
      'twitter': '🐦',
      'facebook': '📘',
      'instagram': '📷'
    };
    return icons[platform] || '📱';
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-bold">📱 ソーシャルメディア管理</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="animate-pulse space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="border rounded-lg p-4">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-bold">📱 ソーシャルメディア管理</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-red-500 mb-4">⚠️ エラーが発生しました</div>
              <div className="text-sm text-gray-600 mb-4">{error}</div>
              <Button onClick={fetchSocialMediaData} size="sm">
                再試行
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">📱 ソーシャルメディア管理</CardTitle>
          {status && (
            <div className="text-sm text-gray-600">
              総チャンネル数: {status.total_channels} | アクティブ: {status.active_channels} | 
              本日の投稿数: {status.total_posts_today} | AIサービス: {status.ai_service_available ? '利用可能' : '利用不可'}
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {channels.map((channel) => (
              <div key={channel.channel_id} className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getPlatformIcon(channel.platform)}</span>
                    <h3 className="font-semibold">{getPlatformDisplayName(channel.platform)}</h3>
                  </div>
                  <Badge variant={getStatusVariant(channel.is_active, channel.auto_posting)}>
                    {getStatusLabel(channel.is_active, channel.auto_posting)}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="font-medium">{channel.channel_name}</div>
                  <div>投稿頻度: {channel.posting_frequency}分</div>
                  <div>自動投稿: {channel.auto_posting ? '有効' : '無効'}</div>
                  <div>自動コメント: {channel.auto_commenting ? '有効' : '無効'}</div>
                  <div className="text-xs text-gray-500">
                    対応災害: {channel.disaster_types.join(', ')}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-6 space-y-4">
            <h4 className="font-semibold">クイックアクション</h4>
            <div className="flex gap-2 flex-wrap">
              <Button 
                size="sm" 
                onClick={() => {
                  // TODO: Implement emergency post functionality
                  console.log('Emergency post clicked');
                }}
              >
                緊急投稿
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => {
                  // TODO: Implement scheduled post functionality
                  console.log('Scheduled post clicked');
                }}
              >
                投稿予約
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => {
                  // TODO: Implement analytics display
                  console.log('Analytics clicked');
                }}
              >
                アナリティクス表示
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={fetchSocialMediaData}
              >
                データ更新
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SocialMediaDashboard; 