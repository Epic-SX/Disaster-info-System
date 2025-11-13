"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';
import Image from 'next/image';
import { 
  Search, 
  Play, 
  Users, 
  Clock, 
  TrendingUp,
  MapPin,
  Filter,
  VideoIcon,
  Radio,
  ChevronRight,
  ExternalLink,
  CheckCircle2
} from 'lucide-react';

interface YouTubeVideo {
  video_id: string;
  title: string;
  channel: string;
  description: string;
  thumbnail: string;
  duration: string;
  views: string;
  published_time: string;
  link: string;
  channel_id?: string;
  channel_url?: string;
  subscriber_count?: string;
  video_type?: string;
  verified_channel?: boolean;
  category?: string;
  tags?: string[];
}

interface YouTubeChannel {
  channel_id: string;
  name: string;
  url: string;
  thumbnail: string;
  subscriber_count: string;
  verified: boolean;
  description?: string;
}

interface SearchResult {
  videos: YouTubeVideo[];
  channels?: YouTubeChannel[];
  total_results: number;
  search_query: string;
  next_page_token?: string;
  related_searches?: string[];
  response_time?: number;
  search_parameters?: any;
}

interface TrendingTopic {
  query: string;
  link?: string;
  thumbnail?: string;
  type?: string;
  count?: number;
}

const YouTubeSearchDashboard: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null);
  const [channels, setChannels] = useState<YouTubeChannel[]>([]);
  const [liveStreams, setLiveStreams] = useState<YouTubeVideo[]>([]);
  const [trendingTopics, setTrendingTopics] = useState<TrendingTopic[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Search filters
  const [searchType, setSearchType] = useState('general');
  const [timeFilter, setTimeFilter] = useState('all');
  const [qualityFilter, setQualityFilter] = useState('all');
  const [location, setLocation] = useState('');
  const [includeShorts, setIncludeShorts] = useState(true);
  
  // Active tab
  const [activeTab, setActiveTab] = useState('search');

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load live streams
      const liveResponse = await apiClient.get<SearchResult>(API_ENDPOINTS.youtube.liveStreams);
      if (liveResponse.videos) {
        setLiveStreams(liveResponse.videos);
      }

      // Load disaster channels
      const channelResponse = await apiClient.get<SearchResult>(`${API_ENDPOINTS.youtube.channels}?limit=10`);
      if (channelResponse.channels) {
        setChannels(channelResponse.channels);
      }

      // Load trending topics
      const trendingResponse = await apiClient.get<{trending_topics: TrendingTopic[]}>(API_ENDPOINTS.youtube.trending);
      if (trendingResponse.trending_topics) {
        setTrendingTopics(trendingResponse.trending_topics);
      }
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('初期データの読み込みに失敗しました');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams({
        query: searchQuery,
        limit: '20',
        search_type: searchType,
        include_shorts: includeShorts.toString()
      });
      
      if (timeFilter && timeFilter !== 'all') params.append('time_filter', timeFilter);
      if (qualityFilter && qualityFilter !== 'all') params.append('quality_filter', qualityFilter);
      
      const response = await apiClient.get<SearchResult>(`${API_ENDPOINTS.youtube.search}?${params}`);
      setSearchResults(response);
    } catch (err) {
      console.error('Search error:', err);
      setError('検索に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleAdvancedSearch = async () => {
    setLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams({
        limit: '30',
        search_type: searchType,
        include_shorts: includeShorts.toString(),
        include_channels: 'true'
      });
      
      if (searchQuery) params.append('query', searchQuery);
      if (timeFilter && timeFilter !== 'all') params.append('time_filter', timeFilter);
      if (qualityFilter && qualityFilter !== 'all') params.append('quality_filter', qualityFilter);
      if (location) params.append('location', location);
      
      const response = await apiClient.get<any>(`${API_ENDPOINTS.youtube.advanced}?${params}`);
      
      // Set different data based on advanced search response
      if (response.videos) setSearchResults({ ...response, videos: response.videos });
      if (response.channels) setChannels(response.channels);
      if (response.live_streams) setLiveStreams(response.live_streams);
      if (response.trending_topics) setTrendingTopics(response.trending_topics);
      
    } catch (err) {
      console.error('Advanced search error:', err);
      setError('高度な検索に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const VideoCard: React.FC<{ video: YouTubeVideo }> = ({ video }) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex gap-4">
          <Image 
            src={video.thumbnail} 
            alt={video.title}
            width={128}
            height={80}
            className="rounded"
          />
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1 line-clamp-2">{video.title}</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
              <span className="flex items-center gap-1">
                {video.verified_channel && <CheckCircle2 className="w-3 h-3 text-blue-500" />}
                {video.channel}
              </span>
              {video.subscriber_count && (
                <Badge variant="outline" className="text-xs">
                  <Users className="w-3 h-3 mr-1" />
                  {video.subscriber_count}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Play className="w-3 h-3" />
                {video.views}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {video.duration}
              </span>
              <span>{video.published_time}</span>
            </div>
            {video.video_type && (
              <Badge variant={video.video_type === 'live' ? 'destructive' : 'secondary'} className="mt-2">
                {video.video_type === 'live' ? (
                  <>
                    <Radio className="w-3 h-3 mr-1" />
                    ライブ
                  </>
                ) : video.video_type === 'short' ? (
                  'ショート'
                ) : (
                  '動画'
                )}
              </Badge>
            )}
          </div>
          <Button size="sm" variant="outline" asChild>
            <a href={video.link} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4" />
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const ChannelCard: React.FC<{ channel: YouTubeChannel }> = ({ channel }) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <Image 
            src={channel.thumbnail} 
            alt={channel.name}
            width={48}
            height={48}
            className="rounded-full"
          />
          <div className="flex-1">
            <h3 className="font-semibold flex items-center gap-1">
              {channel.name}
              {channel.verified && <CheckCircle2 className="w-4 h-4 text-blue-500" />}
            </h3>
            <p className="text-sm text-muted-foreground">{channel.subscriber_count}</p>
            {channel.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{channel.description}</p>
            )}
          </div>
          <Button size="sm" variant="outline" asChild>
            <a href={channel.url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4" />
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <VideoIcon className="w-5 h-5" />
            YouTube災害情報検索
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Search Input */}
            <div className="flex gap-2">
              <Input 
                placeholder="災害関連動画を検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} disabled={loading}>
                <Search className="w-4 h-4 mr-2" />
                検索
              </Button>
            </div>

            {/* Search Filters */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Select value={searchType} onValueChange={setSearchType}>
                <SelectTrigger>
                  <SelectValue placeholder="検索タイプ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">一般</SelectItem>
                  <SelectItem value="live">ライブ</SelectItem>
                  <SelectItem value="recent">最新</SelectItem>
                  <SelectItem value="channels">チャンネル</SelectItem>
                </SelectContent>
              </Select>

              <Select value={timeFilter} onValueChange={setTimeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="期間" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="today">今日</SelectItem>
                  <SelectItem value="this_week">今週</SelectItem>
                  <SelectItem value="this_month">今月</SelectItem>
                </SelectContent>
              </Select>

              <Select value={qualityFilter} onValueChange={setQualityFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="画質" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="hd">HD</SelectItem>
                  <SelectItem value="4k">4K</SelectItem>
                </SelectContent>
              </Select>

              <Input 
                placeholder="地域"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={handleAdvancedSearch} disabled={loading}>
                <Filter className="w-4 h-4 mr-2" />
                高度な検索
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="search">検索結果</TabsTrigger>
          <TabsTrigger value="live">ライブ配信</TabsTrigger>
          <TabsTrigger value="channels">チャンネル</TabsTrigger>
          <TabsTrigger value="trending">トレンド</TabsTrigger>
        </TabsList>

        <TabsContent value="search" className="space-y-4">
          {searchResults && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">
                  検索結果: {searchResults.total_results}件
                </h3>
                {searchResults.response_time && (
                  <Badge variant="outline">
                    {searchResults.response_time.toFixed(2)}秒
                  </Badge>
                )}
              </div>
              
              <ScrollArea className="h-[600px]">
                <div className="space-y-3">
                  {searchResults.videos.map((video) => (
                    <VideoCard key={video.video_id} video={video} />
                  ))}
                </div>
              </ScrollArea>

              {searchResults.related_searches && searchResults.related_searches.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">関連検索</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {searchResults.related_searches.map((search, index) => (
                        <Badge 
                          key={index} 
                          variant="outline" 
                          className="cursor-pointer hover:bg-muted"
                          onClick={() => setSearchQuery(search)}
                        >
                          {search}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="live" className="space-y-4">
          <h3 className="font-semibold">ライブ災害情報配信</h3>
          <ScrollArea className="h-[600px]">
            <div className="space-y-3">
              {liveStreams.map((stream) => (
                <VideoCard key={stream.video_id} video={stream} />
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="channels" className="space-y-4">
          <h3 className="font-semibold">災害情報チャンネル</h3>
          <ScrollArea className="h-[600px]">
            <div className="space-y-3">
              {channels.map((channel) => (
                <ChannelCard key={channel.channel_id} channel={channel} />
              ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="trending" className="space-y-4">
          <h3 className="font-semibold">トレンド災害トピック</h3>
          <ScrollArea className="h-[600px]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {trendingTopics.map((topic, index) => (
                <Card key={index} className="hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => setSearchQuery(topic.query)}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{topic.query}</span>
                      <div className="flex items-center gap-2">
                        {topic.count && (
                          <Badge variant="outline">
                            {topic.count}
                          </Badge>
                        )}
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                    {topic.type && (
                      <Badge variant="secondary" className="mt-2">
                        {topic.type === 'trending_keyword' ? 'キーワード' : '関連検索'}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default YouTubeSearchDashboard; 