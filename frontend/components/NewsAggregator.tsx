import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useWebSocket } from '../hooks/useWebSocket';
import { getWebSocketConfig } from '../config/websocket';

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  url: string;
  published_at: string;
  category: string;
  source: string;
  time_ago?: string;
}

const NewsAggregator: React.FC = () => {
  const [newsItems, setNewsItems] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Memoize WebSocket configuration to prevent unnecessary re-renders
  const wsConfig = useMemo(() => getWebSocketConfig(), []);

  // WebSocket connection for real-time updates
  const { isConnected } = useWebSocket({
    url: wsConfig.url,
    fallbackUrls: wsConfig.fallbackUrls,
    onMessage: (message) => {
      if (message.type === 'news_update') {
        setNewsItems(message.data || []);
        setLoading(false);
        setError(null);
      }
    },
    onOpen: () => {
      console.log('WebSocket connected for news updates');
    },
    onClose: () => {
      console.log('WebSocket disconnected for news updates');
    },
    onError: (error) => {
      console.error('WebSocket error for news updates:', error);
    }
  });

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/news');
        if (!response.ok) {
          throw new Error('Failed to fetch news');
        }
        const data = await response.json();
        setNewsItems(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        console.error('Error fetching news:', err);
      } finally {
        setLoading(false);
      }
    };

    // Only fetch initially if WebSocket is not connected
    if (!isConnected) {
      fetchNews();
    }
    
    // Fallback: refresh news every 5 minutes if WebSocket fails
    const interval = setInterval(fetchNews, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [isConnected]);

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'official': return '公式';
      case 'weather': return '気象';
      case 'training': return '訓練';
      default: return category;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">📰 ニュース・お知らせ</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="border-b pb-3 last:border-b-0 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
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
          <CardTitle className="text-xl font-bold">📰 ニュース・お知らせ</CardTitle>
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
          <CardTitle className="text-xl font-bold">📰 ニュース・お知らせ</CardTitle>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-500">
              {isConnected ? 'リアルタイム' : 'オフライン'}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {newsItems.length === 0 ? (
            <div className="text-center py-4 text-gray-500">
              ニュースがありません
            </div>
          ) : (
            newsItems.map((item) => (
              <div key={item.id} className="border-b pb-3 last:border-b-0">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-sm">{item.title}</h3>
                  <Badge variant="outline" className="ml-2">
                    {getCategoryLabel(item.category)}
                  </Badge>
                </div>
                <div className="text-xs text-gray-600">
                  {item.source} • {item.time_ago || '時間不明'}
                </div>
                {item.summary && (
                  <div className="text-xs text-gray-500 mt-1">
                    {item.summary}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default NewsAggregator; 