"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { YouTubePlayerHybrid } from './YouTubePlayer';
import { 
  Camera, 
  Radio, 
  Tv, 
  Globe, 
  AlertTriangle,
  Clock,
  Users,
  Volume2,
  VolumeX
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
}

const LIVE_STREAMS: LiveStream[] = [
  {
    id: 'nhk-news',
    videoId: 'jfKfPfyJRdk', // NHK WORLD JAPAN live stream
    title: 'NHKニュース ライブ配信',
    channel: 'NHK',
    description: 'NHKの24時間ライブニュース配信',
    category: 'news',
    isLive: true
  },
  {
    id: 'weather-news',
    videoId: 'Ch_ZqaUQhc8', // Weather News 24h
    title: 'ウェザーニュース ライブ',
    channel: 'Weather News',
    description: '24時間天気予報・災害情報',
    category: 'weather',
    isLive: true
  },
  {
    id: 'tbs-news',
    videoId: 'VUqg_FhBn3Y', // TBS NEWS DIG Powered by JNN
    title: 'TBS NEWS ライブ',
    channel: 'TBS',
    description: 'TBSニュース24時間配信',
    category: 'news',
    isLive: true
  },
  {
    id: 'fuji-news',
    videoId: 'aNWYXjH8pdY', // FNNプライムオンライン
    title: 'フジニュースネットワーク',
    channel: 'FNN',
    description: 'フジテレビニュース配信',
    category: 'news',
    isLive: true
  }
];

export function YouTubeLiveStreams() {
  const [selectedStream, setSelectedStream] = useState<LiveStream>(LIVE_STREAMS[0]);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    // Update timestamp every minute
    const interval = setInterval(() => {
      setLastUpdated(new Date());
    }, 60000);

    return () => clearInterval(interval);
  }, []);

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

  return (
    <div className="space-y-6">
      {/* Main Stream Player */}
      <Card className="bg-white/10 backdrop-blur-md border-white/20">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2 text-sm">
              <Camera className="h-4 w-4 text-red-500" />
              {selectedStream.title}
              <Badge className="bg-red-500 text-white text-xs ml-2 animate-pulse">
                LIVE
              </Badge>
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsMuted(!isMuted)}
                className="text-white hover:bg-white/20"
              >
                {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>
              <Badge variant="outline" className="text-white border-white/30 text-xs">
                <Users className="h-3 w-3 mr-1" />
                {selectedStream.viewerCount?.toLocaleString() || '--'}
              </Badge>
            </div>
          </div>
          <p className="text-gray-300 text-xs">{selectedStream.description}</p>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg overflow-hidden">
            <YouTubePlayerHybrid
              videoId={selectedStream.videoId}
              title={selectedStream.title}
              autoplay={true}
              muted={isMuted}
              controls={true}
              className="w-full h-full"
            />
          </div>
          
          {/* Stream Info */}
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="outline" className="text-white border-white/30">
              🔴 リアルタイム配信
            </Badge>
            <Badge variant="outline" className="text-white border-white/30">
              📺 {selectedStream.channel}
            </Badge>
            <Badge 
              variant="outline" 
              className={`text-white border-white/30 ${getCategoryColor(selectedStream.category)}`}
            >
              {getCategoryIcon(selectedStream.category)}
              <span className="ml-1">
                {selectedStream.category === 'news' && 'ニュース'}
                {selectedStream.category === 'weather' && '天気'}
                {selectedStream.category === 'emergency' && '緊急'}
                {selectedStream.category === 'camera' && 'カメラ'}
              </span>
            </Badge>
            <Badge variant="outline" className="text-white border-white/30">
              <Clock className="h-3 w-3 mr-1" />
              更新: {lastUpdated.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Stream Selection Grid */}
      <Card className="bg-white/10 backdrop-blur-md border-white/20">
        <CardHeader>
          <CardTitle className="text-white text-sm">配信チャンネル選択</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {LIVE_STREAMS.map((stream) => (
              <div
                key={stream.id}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedStream.id === stream.id
                    ? 'border-red-500 bg-red-500/20'
                    : 'border-white/20 bg-white/5 hover:bg-white/10'
                }`}
                onClick={() => setSelectedStream(stream)}
              >
                <div className="flex items-center gap-2 mb-2">
                  {getCategoryIcon(stream.category)}
                  <span className="text-white text-sm font-medium">{stream.channel}</span>
                  {stream.isLive && (
                    <Badge className="bg-red-500 text-white text-xs animate-pulse">
                      LIVE
                    </Badge>
                  )}
                </div>
                <p className="text-gray-300 text-xs">{stream.title}</p>
                <p className="text-gray-400 text-xs mt-1">{stream.description}</p>
              </div>
            ))}
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