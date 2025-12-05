"use client";

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  RefreshCw
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
    title: 'NHKニュース ライブ配信',
    channel: 'NHK',
    description: 'NHKの24時間ライブニュース配信',
    category: 'news',
    isLive: true
  },
  {
    id: 'weather-news',
    videoId: 'Ch_ZqaUQhc8',
    title: 'ウェザーニュース ライブ',
    channel: 'Weather News',
    description: '24時間天気予報・災害情報',
    category: 'weather',
    isLive: true
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
      const response = await apiClient.get<{streams?: BackendLiveStream[], videos?: BackendLiveStream[]}>(
        `${API_ENDPOINTS.youtube.liveStreams}?location=Japan`
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
          category: determineCategoryFromTitle(stream.title, stream.channel),
          isLive: stream.video_type === 'live',
          thumbnail: stream.thumbnail,
          link: stream.link,
          verified_channel: stream.verified_channel
        }));
        
        setLiveStreams([...DEFAULT_STREAMS, ...convertedStreams]);
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
  }, [loadLiveStreams]);

  const determineCategoryFromTitle = (title: string, channel: string): LiveStream['category'] => {
    const titleLower = title.toLowerCase();
    const channelLower = channel.toLowerCase();
    
    if (titleLower.includes('weather') || titleLower.includes('ウェザー') || titleLower.includes('天気')) {
      return 'weather';
    }
    if (titleLower.includes('emergency') || titleLower.includes('災害') || titleLower.includes('緊急')) {
      return 'emergency';
    }
    if (titleLower.includes('camera') || titleLower.includes('カメラ') || titleLower.includes('ライブカメラ')) {
      return 'camera';
    }
    return 'news';
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

  // Helper function to get YouTube thumbnail URL
  const getThumbnailUrl = (videoId: string, thumbnail?: string): string => {
    if (thumbnail) {
      return thumbnail;
    }
    // Fallback to YouTube's thumbnail API
    return `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
  };

  return (
    <div className="space-y-6">
      {/* Main Stream Player */}
      <Card className="bg-white/10 backdrop-blur-md border-white/20">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2 text-sm">
              <Camera className="h-4 w-4 text-red-500" />
              {liveStreams.find(stream => stream.videoId === selectedStream)?.title}
              <Badge className="bg-red-500 text-white text-xs ml-2 animate-pulse">
                LIVE
              </Badge>
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
                {liveStreams.find(stream => stream.videoId === selectedStream)?.viewerCount?.toLocaleString() || '--'}
              </Badge>
            </div>
          </div>
          <p className="text-gray-300 text-xs">{liveStreams.find(stream => stream.videoId === selectedStream)?.description}</p>
        </CardHeader>
        <CardContent className="p-4">
          {selectedStream ? (
            <div className="aspect-video bg-gray-800 rounded-lg overflow-hidden">
              <YouTubePlayerHybrid
                videoId={selectedStream}
                title={liveStreams.find(stream => stream.videoId === selectedStream)?.title || ''}
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
          {selectedStream && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge variant="outline" className="text-white border-white/30">
                🔴 リアルタイム配信
              </Badge>
              <Badge variant="outline" className="text-white border-white/30">
                📺 {liveStreams.find(stream => stream.videoId === selectedStream)?.channel || ''}
              </Badge>
              <Badge 
                variant="outline" 
                className={`text-white border-white/30 ${getCategoryColor(liveStreams.find(stream => stream.videoId === selectedStream)?.category || 'news')}`}
              >
                {getCategoryIcon(liveStreams.find(stream => stream.videoId === selectedStream)?.category || 'news')}
                <span className="ml-1">
                  {liveStreams.find(stream => stream.videoId === selectedStream)?.category === 'news' && 'ニュース'}
                  {liveStreams.find(stream => stream.videoId === selectedStream)?.category === 'weather' && '天気'}
                  {liveStreams.find(stream => stream.videoId === selectedStream)?.category === 'emergency' && '緊急'}
                  {liveStreams.find(stream => stream.videoId === selectedStream)?.category === 'camera' && 'カメラ'}
                </span>
              </Badge>
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
            <CardTitle className="text-white text-sm">配信チャンネル選択</CardTitle>
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
                  key={stream.id}
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
                      onError={(e) => {
                        // Fallback to hqdefault if maxresdefault fails
                        const target = e.target as HTMLImageElement;
                        if (target.src.includes('maxresdefault')) {
                          target.src = `https://img.youtube.com/vi/${stream.videoId}/hqdefault.jpg`;
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
                    {/* Category icon overlay */}
                    <div className="absolute top-2 left-2">
                      <div className={`${getCategoryColor(stream.category)} text-white p-1.5 rounded`}>
                        {getCategoryIcon(stream.category)}
                      </div>
                    </div>
                  </div>
                  
                  {/* Card Content */}
                  <div className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-white text-sm font-medium line-clamp-1">{stream.channel}</span>
                    </div>
                    <p className="text-gray-300 text-xs line-clamp-2 mb-1">{stream.title}</p>
                    <p className="text-gray-400 text-xs line-clamp-1">{stream.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Emergency Alert Stream (if active) */}
      <Card className="bg-red-500/20 border-red-500/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            緊急災害情報配信
            <Badge className="bg-red-600 text-white text-xs">
              待機中
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="text-center py-8">
            <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
            <p className="text-white text-sm">現在、緊急災害情報の配信はありません</p>
            <p className="text-gray-300 text-xs mt-1">
              災害発生時には自動的に緊急配信に切り替わります
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 

export default YouTubeLiveStreams; 