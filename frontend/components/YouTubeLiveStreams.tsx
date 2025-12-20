"use client";

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { YouTubePlayerHybrid } from './YouTubePlayer';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';
import Image from 'next/image';
import { 
  Camera, 
  Radio, 
  Tv, 
  Globe, 
  AlertTriangle,
  Clock,
  Users,
  Volume2,
  VolumeX,
  RefreshCw,
  Info
} from 'lucide-react';

interface LiveStream {
  id: string;
  videoId: string;
  title: string;
  channel: string;
  description: string;
  category: 'news' | 'weather' | 'emergency' | 'camera';
  isLive: boolean;
  viewerCount?: number;
  thumbnail?: string;
  link?: string;
  verified_channel?: boolean;
  priority?: 'high' | 'medium' | 'low';
}

interface BackendLiveStream {
  video_id: string;
  title: string;
  channel: string;
  description?: string;
  video_type?: string;
  duration?: string;
  thumbnail?: string;
  link?: string;
  verified_channel?: boolean;
}

// Default/fallback streams - moved outside component to avoid dependency issues
const DEFAULT_STREAMS: LiveStream[] = [
  {
    id: 'nhk-news',
    videoId: 'jfKfPfyJRdk',
    title: 'NHK 災害・気象情報',
    channel: 'NHK',
    description: '災害時の最新情報と避難指示をお伝えします',
    category: 'emergency',
    isLive: true,
    priority: 'high'
  },
  {
    id: 'weather-news',
    videoId: 'Ch_ZqaUQhc8',
    title: 'ウェザーニュース ライブ',
    channel: 'Weather News',
    description: '24時間天気予報・災害情報',
    category: 'weather',
    isLive: true,
    priority: 'high'
  }
];

export function YouTubeLiveStreams() {
  const [selectedStream, setSelectedStream] = useState<string>(DEFAULT_STREAMS[0].videoId);
  const [liveStreams, setLiveStreams] = useState<LiveStream[]>(DEFAULT_STREAMS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [muted, setMuted] = useState(false);

  const loadLiveStreams = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      // Load live disaster streams from backend API
      // Using location=Japan and focusing on disaster/community keywords like Community feature
      const response = await apiClient.get<{streams?: BackendLiveStream[], videos?: BackendLiveStream[]}>(
        `${API_ENDPOINTS.youtube.liveStreams}?location=Japan&query=災害情報,避難情報,コミュニティ`
      );
      
      // Convert backend format to frontend format
      const backendStreams = response.videos || response.streams || [];
      
      if (backendStreams.length > 0) {
        const convertedStreams: LiveStream[] = backendStreams.map((stream, index) => ({
          id: stream.video_id || `stream-${index}`,
          videoId: stream.video_id,
          title: stream.title,
          channel: stream.channel,
          description: stream.description || '',
          category: determineCategoryFromContent(stream.title, stream.channel, stream.description || ''),
          isLive: stream.video_type === 'live',
          thumbnail: stream.thumbnail,
          link: stream.link,
          verified_channel: stream.verified_channel,
          priority: determinePriority(stream.title, stream.channel)
        }));
        
        // Filter out duplicates by videoId and combine with default streams
        const defaultVideoIds = new Set(DEFAULT_STREAMS.map(s => s.videoId));
        const uniqueBackendStreams = convertedStreams.filter(
          stream => !defaultVideoIds.has(stream.videoId)
        );
        
        // Remove duplicates within backend streams by videoId
        const seenVideoIds = new Set<string>();
        const deduplicatedBackendStreams = uniqueBackendStreams.filter(stream => {
          if (seenVideoIds.has(stream.videoId)) {
            return false;
          }
          seenVideoIds.add(stream.videoId);
          return true;
        });
        
        // Sort by priority (high first) and merge with defaults
        const sortedStreams = [...DEFAULT_STREAMS, ...deduplicatedBackendStreams].sort((a, b) => {
          const priorityOrder = { high: 0, medium: 1, low: 2 };
          return priorityOrder[a.priority || 'low'] - priorityOrder[b.priority || 'low'];
        });
        
        setLiveStreams(sortedStreams);
      } else {
        // Fallback to default streams if no results
        setLiveStreams(DEFAULT_STREAMS);
      }
    } catch (err) {
      console.error('Error loading live streams:', err);
      setError('ライブ配信の読み込みに失敗しました');
      setLiveStreams(DEFAULT_STREAMS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initialize with default streams on mount, then load live streams
    setLiveStreams(DEFAULT_STREAMS);
    setSelectedStream(DEFAULT_STREAMS[0].videoId);
    
    // Load live streams from API after initial render
    loadLiveStreams();
    
    // Auto-refresh every 5 minutes to get latest live streams
    const refreshInterval = setInterval(() => {
      loadLiveStreams();
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(refreshInterval);
  }, [loadLiveStreams]);

  const determineCategoryFromContent = (
    title: string, 
    channel: string, 
    description: string
  ): LiveStream['category'] => {
    const content = `${title} ${channel} ${description}`.toLowerCase();
    
    if (content.includes('weather') || content.includes('ウェザー') || content.includes('天気')) {
      return 'weather';
    }
    if (content.includes('emergency') || content.includes('災害') || content.includes('緊急') || content.includes('避難')) {
      return 'emergency';
    }
    if (content.includes('camera') || content.includes('カメラ') || content.includes('ライブカメラ')) {
      return 'camera';
    }
    return 'news';
  };

  const determinePriority = (title: string, channel: string): LiveStream['priority'] => {
    const content = `${title} ${channel}`.toLowerCase();
    
    if (content.includes('緊急') || content.includes('emergency') || content.includes('nhk') || content.includes('気象庁')) {
      return 'high';
    }
    if (content.includes('重要') || content.includes('important')) {
      return 'medium';
    }
    return 'low';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'news':
        return <Tv className="h-4 w-4" />;
      case 'weather':
        return <Globe className="h-4 w-4" />;
      case 'emergency':
        return <AlertTriangle className="h-4 w-4" />;
      case 'camera':
        return <Camera className="h-4 w-4" />;
      default:
        return <Radio className="h-4 w-4" />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'news':
        return 'bg-blue-500';
      case 'weather':
        return 'bg-green-500';
      case 'emergency':
        return 'bg-red-500';
      case 'camera':
        return 'bg-purple-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'news':
        return 'ニュース';
      case 'weather':
        return '天気';
      case 'emergency':
        return '緊急';
      case 'camera':
        return 'カメラ';
      default:
        return 'その他';
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-600';
      case 'medium':
        return 'bg-yellow-600';
      case 'low':
        return 'bg-gray-600';
      default:
        return 'bg-gray-600';
    }
  };

  // Helper function to get YouTube thumbnail URL
  const getThumbnailUrl = (videoId: string, thumbnail?: string): string => {
    if (thumbnail) {
      return thumbnail;
    }
    // Use i.ytimg.com which is more reliable than img.youtube.com
    // Try hqdefault first as maxresdefault might not exist for all videos
    return `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
  };

  const selectedStreamData = liveStreams.find(stream => stream.videoId === selectedStream);

  return (
    <div className="space-y-6">
      {/* Information Banner */}
      <Card className="bg-blue-500/20 border-blue-500/50">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-white font-semibold text-sm mb-1">YouTube Live機能について</h3>
              <p className="text-gray-200 text-xs leading-relaxed">
                災害時の同時アクセス増加に対応するため、YouTube Liveのインフラを活用して有益な災害情報を配信します。
                サーバー負荷を分散し、安定した情報提供を実現します。複数のメンバーがYouTubeを活用してコミュニティを運営しています。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Stream Player */}
      <Card className="bg-white/10 backdrop-blur-md border-white/20">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2 text-sm">
              <Camera className="h-4 w-4 text-red-500" />
              {selectedStreamData?.title || '配信を選択してください'}
              {selectedStreamData?.isLive && (
                <Badge className="bg-red-500 text-white text-xs ml-2 animate-pulse">
                  LIVE
                </Badge>
              )}
              {selectedStreamData?.priority === 'high' && (
                <Badge className="bg-red-600 text-white text-xs ml-1">
                  重要
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setMuted(!muted)}
                className="text-white hover:bg-white/20"
              >
                {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>
              <Badge variant="outline" className="text-white border-white/30 text-xs">
                <Users className="h-3 w-3 mr-1" />
                {selectedStreamData?.viewerCount?.toLocaleString() || '--'}
              </Badge>
            </div>
          </div>
          <p className="text-gray-300 text-xs">{selectedStreamData?.description}</p>
        </CardHeader>
        <CardContent className="p-4">
          {selectedStream ? (
            <div className="aspect-video bg-gray-800 rounded-lg overflow-hidden">
              <YouTubePlayerHybrid
                videoId={selectedStream}
                title={selectedStreamData?.title || ''}
                autoplay={true}
                muted={muted}
                controls={true}
                className="w-full h-full"
              />
            </div>
          ) : (
            <div className="aspect-video bg-gray-800 rounded-lg overflow-hidden flex items-center justify-center">
              <div className="text-center">
                <Tv className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-white text-lg">配信を選択してください</p>
                <p className="text-gray-400 text-sm">下から視聴したい配信を選んでください</p>
              </div>
            </div>
          )}
          
          {/* Stream Info */}
          {selectedStream && selectedStreamData && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge variant="outline" className="text-white border-white/30">
                🔴 リアルタイム配信
              </Badge>
              <Badge variant="outline" className="text-white border-white/30">
                📺 {selectedStreamData.channel}
              </Badge>
              <Badge 
                variant="outline" 
                className={`text-white border-white/30 ${getCategoryColor(selectedStreamData.category)}`}
              >
                {getCategoryIcon(selectedStreamData.category)}
                <span className="ml-1">
                  {getCategoryLabel(selectedStreamData.category)}
                </span>
              </Badge>
              {selectedStreamData.priority && (
                <Badge 
                  variant="outline" 
                  className={`text-white border-white/30 ${getPriorityColor(selectedStreamData.priority)}`}
                >
                  {selectedStreamData.priority === 'high' && '🔴 重要'}
                  {selectedStreamData.priority === 'medium' && '🟡 中'}
                  {selectedStreamData.priority === 'low' && '⚪ 低'}
                </Badge>
              )}
              <Badge variant="outline" className="text-white border-white/30">
                <Clock className="h-3 w-3 mr-1" />
                更新: {new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stream Selection Grid */}
      <Card className="bg-white/10 backdrop-blur-md border-white/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Camera className="h-4 w-4" />
              YouTube Live災害情報配信
            </CardTitle>
            <Button
              size="sm"
              variant="ghost"
              onClick={loadLiveStreams}
              disabled={loading}
              className="text-white hover:bg-white/20"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          {error && (
            <div className="text-red-400 text-xs mt-2">{error}</div>
          )}
          <p className="text-gray-300 text-xs mt-2">
            災害時の有益な情報をYouTube Liveで配信しています。サーバー負荷を分散し、安定した情報提供を実現します。
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {liveStreams.map((stream) => {
              const handleCardClick = () => {
                // Set selected stream to play in the player above
                setSelectedStream(stream.videoId);
                
                // Open the video link in a new tab
                const videoUrl = stream.link || `https://www.youtube.com/watch?v=${stream.videoId}`;
                window.open(videoUrl, '_blank', 'noopener,noreferrer');
              };

              const thumbnailUrl = getThumbnailUrl(stream.videoId, stream.thumbnail);

              return (
                <div
                  key={stream.videoId}
                  className={`rounded-lg border cursor-pointer transition-all overflow-hidden ${
                    selectedStream === stream.videoId
                      ? 'border-red-500 bg-red-500/20'
                      : 'border-white/20 bg-white/5 hover:bg-white/10'
                  }`}
                  onClick={handleCardClick}
                >
                  {/* Thumbnail Image */}
                  <div className="relative w-full aspect-video bg-gray-800">
                    <Image
                      src={thumbnailUrl}
                      alt={stream.title}
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                      unoptimized={true}
                      onError={(e) => {
                        // Fallback to default quality if hqdefault fails
                        const target = e.target as HTMLImageElement;
                        if (!target.src.includes('default.jpg')) {
                          target.src = `https://i.ytimg.com/vi/${stream.videoId}/default.jpg`;
                        }
                      }}
                    />
                    {/* Live badge overlay */}
                    {stream.isLive && (
                      <div className="absolute top-2 right-2">
                        <Badge className="bg-red-500 text-white text-xs animate-pulse">
                          LIVE
                        </Badge>
                      </div>
                    )}
                    {/* Priority badge */}
                    {stream.priority === 'high' && (
                      <div className="absolute top-2 left-2">
                        <Badge className="bg-red-600 text-white text-xs">
                          重要
                        </Badge>
                      </div>
                    )}
                    {/* Category icon overlay */}
                    <div className={`absolute bottom-2 left-2 ${stream.priority === 'high' ? 'top-12' : 'top-2'}`}>
                      <div className={`${getCategoryColor(stream.category)} text-white p-1.5 rounded`}>
                        {getCategoryIcon(stream.category)}
                      </div>
                    </div>
                  </div>
                  
                  {/* Card Content */}
                  <div className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-white text-sm font-medium line-clamp-1">{stream.channel}</span>
                      {stream.verified_channel && (
                        <Badge className="bg-blue-500 text-white text-xs px-1">✓</Badge>
                      )}
                    </div>
                    <p className="text-gray-300 text-xs line-clamp-2 mb-1">{stream.title}</p>
                    <div className="flex items-center gap-1 mb-1">
                      <Badge 
                        variant="outline" 
                        className={`text-xs border-white/30 ${getCategoryColor(stream.category)} text-white`}
                      >
                        {getCategoryLabel(stream.category)}
                      </Badge>
                    </div>
                    <p className="text-gray-400 text-xs line-clamp-1">{stream.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* YouTube Live Support Information */}
      <Card className="bg-green-500/20 border-green-500/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Info className="h-4 w-4 text-green-400" />
            YouTube Live活用情報
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="text-center py-4">
            <p className="text-white text-sm mb-2">
              YouTube Liveを活用した災害情報配信により、サーバー負荷を分散しています
            </p>
            <p className="text-gray-300 text-xs">
              災害発生時でも安定した情報提供が可能です。複数のメンバーがYouTubeを活用してコミュニティを運営しています。最新の避難情報や安全ガイドを確認してください。
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 

export default YouTubeLiveStreams; 