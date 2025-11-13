'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  MessageCircle, 
  Users, 
  TrendingUp, 
  Send, 
  Bot, 
  AlertTriangle,
  MessageSquare,
  Activity,
  BarChart3
} from 'lucide-react';
import { apiClient, API_ENDPOINTS, createWebSocket, WS_ENDPOINTS } from '@/lib/api-config';

interface ChatMessage {
  id: string;
  message_id: string;
  author: string;
  message: string;
  timestamp: string;
  sentiment_score: number;
  category: string;
  platform: string;
}

interface ChatAnalytics {
  total_messages: number;
  disaster_mentions: number;
  product_mentions: number;
  sentiment_score: number;
  top_keywords: string[];
  active_users: number;
}

interface AutoResponse {
  id: number;
  trigger_keywords: string;
  response_text: string;
  response_type: string;
  used_count: number;
  last_used_at: string | null;
}

export default function YouTubeChatDashboard() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [analytics, setAnalytics] = useState<ChatAnalytics | null>(null);
  const [autoResponses, setAutoResponses] = useState<AutoResponse[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'>('disconnected');
  const [manualResponse, setManualResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fallback HTTP polling for chat data
  const startChatPolling = useCallback(() => {
    console.log('Starting HTTP polling for chat data');
    setConnectionStatus('connected');
    setError('Using HTTP polling');
    
    const pollInterval = setInterval(async () => {
      try {
        // Inline the fetch functions to avoid dependency issues
        const [messagesData, analyticsData, responsesData] = await Promise.all([
          apiClient.get(`${API_ENDPOINTS.chat.messages}?limit=50`),
          apiClient.get(API_ENDPOINTS.chat.analytics),
          apiClient.get(API_ENDPOINTS.chat.responses)
        ]);
        
        setMessages(messagesData);
        setAnalytics(analyticsData);
        setAutoResponses(responsesData);
      } catch (err) {
        console.error('Chat polling error:', err);
      }
    }, 5000); // Poll every 5 seconds

    return pollInterval;
  }, []);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    const maxRetries = 3;
    let reconnectAttempts = 0;
    
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      setConnectionStatus('connecting');
      const ws = createWebSocket(WS_ENDPOINTS.main);
      
      // Handle case where WebSocket creation fails or is not available
      if (!ws) {
        console.log('WebSocket not available for chat, falling back to HTTP polling');
        setConnectionStatus('disconnected');
        startChatPolling();
        return;
      }
      
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Chat WebSocket connected');
        setConnectionStatus('connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'chat_message') {
            setMessages(prev => [...prev, data.message].slice(-100)); // Keep last 100 messages
          } else if (data.type === 'chat_analytics') {
            setAnalytics(data.analytics);
          } else if (data.type === 'auto_response') {
            setAutoResponses(prev => [...prev, data.response].slice(-50)); // Keep last 50 responses
          }
        } catch (err) {
          console.error('Error parsing chat WebSocket message:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('Chat WebSocket disconnected:', event.code, event.reason);
        setConnectionStatus('disconnected');
        setIsConnected(false);
        
        if (reconnectAttempts < maxRetries) {
          reconnectAttempts++;
          console.log(`Attempting chat WebSocket reconnect ${reconnectAttempts}/${maxRetries}`);
          setTimeout(connectWebSocket, 5000);
        } else {
          console.log('Max WebSocket reconnect attempts reached, falling back to HTTP polling');
          startChatPolling();
        }
      };

      ws.onerror = (error) => {
        console.error('Chat WebSocket error:', error);
        setConnectionStatus('error');
        setError('WebSocket connection error');
      };

    } catch (error) {
      console.error('Failed to connect chat WebSocket:', error);
      setConnectionStatus('error');
      setError('Failed to establish WebSocket connection');
      startChatPolling();
    }
  }, [startChatPolling]);

  // Initial connection and data fetch
  useEffect(() => {
    console.log('🚀 YouTubeChatDashboard mounted, initializing...');
    
    // Skip during build time
    if (typeof window === 'undefined') { // Check if it's running in a browser environment
      console.log('⏭️ Skipping WebSocket during build time');
      return;
    }
    
    // Inline initial data fetch to avoid dependency issues
    const fetchInitialData = async () => {
      setIsLoading(true);
      try {
        // Fetch recent messages using the new API client
        const messagesData = await apiClient.get(`${API_ENDPOINTS.chat.messages}?limit=50`);
        setMessages(messagesData);

        // Fetch analytics
        const analyticsData = await apiClient.get(API_ENDPOINTS.chat.analytics);
        setAnalytics(analyticsData);

        // Fetch auto-responses
        const responsesData = await apiClient.get(API_ENDPOINTS.chat.responses);
        setAutoResponses(responsesData);
      } catch (error) {
        setError('Failed to fetch initial data');
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchInitialData();
    
    // Connect WebSocket after a small delay to ensure component is fully mounted
    const connectTimer = setTimeout(() => {
      connectWebSocket();
    }, 1000);
    
    return () => {
      clearTimeout(connectTimer);
      if (wsRef.current) {
        console.log('🧹 Cleaning up WebSocket connection');
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connectWebSocket]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const testConnection = async () => {
    console.log('🧪 Testing WebSocket connection...');
    setError(null);
    
    try {
      // First test if the backend is reachable using the new API client
      const healthData = await apiClient.get(API_ENDPOINTS.health);
      console.log('✅ Backend health check passed:', healthData);
      
      // Now test WebSocket
      connectWebSocket();
    } catch (error) {
      setError('Cannot reach backend server');
      console.error('❌ Backend health check failed:', error);
    }
  };

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      console.log('🔌 Manually disconnecting WebSocket');
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
      setIsConnected(false);
    }
  };

  const sendManualResponse = async () => {
    if (!manualResponse.trim()) return;
    
    try {
      await apiClient.post(API_ENDPOINTS.chat.response, { message: manualResponse });
      setManualResponse('');
      
      // Add the sent message to our local state
      const sentMessage: ChatMessage = {
        id: `manual_${Date.now()}`,
        message_id: `manual_${Date.now()}`,
        author: 'Bot (Manual)',
        message: manualResponse,
        timestamp: new Date().toISOString(),
        sentiment_score: 1,
        category: 'manual',
        platform: 'youtube'
      };
      setMessages(prev => [...prev, sentMessage]);
    } catch (error) {
      setError('Failed to send message');
      console.error('Failed to send message:', error);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.1) return 'text-green-600';
    if (score < -0.1) return 'text-red-600';
    return 'text-gray-600';
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.1) return '😊';
    if (score < -0.1) return '😔';
    return '😐';
  };

  const getCategoryBadgeColor = (category: string) => {
    switch (category) {
      case 'disaster': return 'bg-red-100 text-red-800';
      case 'product': return 'bg-blue-100 text-blue-800';
      case 'general': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p>チャットダッシュボードを読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <Alert className={
        connectionStatus === 'connected' ? 'border-green-200 bg-green-50' : 
        connectionStatus === 'connecting' || connectionStatus === 'reconnecting' ? 'border-yellow-200 bg-yellow-50' :
        'border-red-200 bg-red-50'
      }>
        <Activity className={`h-4 w-4 ${
          connectionStatus === 'connected' ? 'text-green-600' : 
          connectionStatus === 'connecting' || connectionStatus === 'reconnecting' ? 'text-yellow-600 animate-spin' :
          'text-red-600'
        }`} />
        <AlertDescription>
          チャットサービスの状態: <strong>
            {connectionStatus === 'connected' ? '接続済み' : 
             connectionStatus === 'connecting' ? '接続中...' :
             connectionStatus === 'reconnecting' ? '再接続中...' :
             connectionStatus === 'error' ? 'エラー' :
             '切断中'}
          </strong>
          {error && <span className="text-red-600 ml-2">({error})</span>}
        </AlertDescription>
      </Alert>

      {/* Analytics Overview */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">総メッセージ数</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics.total_messages}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">アクティブユーザー</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{analytics.active_users}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">災害関連メッセージ</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{analytics.disaster_mentions}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">商品関連メッセージ</CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{analytics.product_mentions}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Dashboard */}
      <Tabs defaultValue="chat" className="space-y-4">
        <TabsList>
          <TabsTrigger value="chat">ライブチャット</TabsTrigger>
          <TabsTrigger value="analytics">分析</TabsTrigger>
          <TabsTrigger value="responses">自動応答</TabsTrigger>
          <TabsTrigger value="controls">コントロール</TabsTrigger>
        </TabsList>

        {/* Live Chat Tab */}
        <TabsContent value="chat" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageCircle className="h-5 w-5" />
                YouTubeライブチャット
              </CardTitle>
              <CardDescription>
                感情分析とカテゴリ分類によるリアルタイムチャットメッセージ
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 w-full border rounded-md p-4">
                <div className="space-y-3">
                  {messages.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">
                      まだメッセージがありません。チャットアクティビティを待機中...
                    </p>
                  ) : (
                    messages.map((message) => (
                      <div key={message.id} className="flex flex-col space-y-1 p-3 border rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">{message.author}</span>
                            <Badge className={getCategoryBadgeColor(message.category)}>
                              {message.category === 'disaster' ? '災害' : 
                               message.category === 'product' ? '商品' : 
                               message.category === 'general' ? '一般' : message.category}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <span className={getSentimentColor(message.sentiment_score)}>
                              {getSentimentIcon(message.sentiment_score)}
                            </span>
                            <span>{new Date(message.timestamp).toLocaleTimeString('ja-JP')}</span>
                          </div>
                        </div>
                        <p className="text-gray-800">{message.message}</p>
                        {message.sentiment_score !== 0 && (
                          <div className="flex items-center gap-2 text-xs">
                            <span>感情:</span>
                            <Progress 
                              value={(message.sentiment_score + 1) * 50} 
                              className="w-20 h-2"
                            />
                            <span className={getSentimentColor(message.sentiment_score)}>
                              {message.sentiment_score > 0 ? 'ポジティブ' : 
                               message.sentiment_score < 0 ? 'ネガティブ' : '中立'}
                            </span>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          {analytics && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    チャット感情分析
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-2">
                        <span>全体的な感情</span>
                        <span className={getSentimentColor(analytics.sentiment_score)}>
                          {analytics.sentiment_score > 0 ? 'ポジティブ' : 
                           analytics.sentiment_score < 0 ? 'ネガティブ' : '中立'}
                        </span>
                      </div>
                      <Progress 
                        value={(analytics.sentiment_score + 1) * 50} 
                        className="w-full"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>トップキーワード</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {analytics.top_keywords.map((keyword, index) => (
                      <Badge key={index} variant="outline">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* Auto Responses Tab */}
        <TabsContent value="responses" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                設定済み自動応答
              </CardTitle>
              <CardDescription>
                キーワードトリガーに基づく自動応答
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {autoResponses.map((response) => (
                  <div key={response.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-semibold">キーワード: {response.trigger_keywords}</h4>
                        <p className="text-sm text-gray-600 mt-1">{response.response_text}</p>
                      </div>
                      <div className="text-right text-sm text-gray-500">
                        <div>使用回数: {response.used_count}</div>
                        {response.last_used_at && (
                          <div>最終使用: {new Date(response.last_used_at).toLocaleString('ja-JP')}</div>
                        )}
                      </div>
                    </div>
                    <Badge variant="outline">{response.response_type}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Controls Tab */}
        <TabsContent value="controls" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Send className="h-5 w-5" />
                手動応答
              </CardTitle>
              <CardDescription>
                チャットに手動でメッセージを送信
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="応答メッセージを入力..."
                value={manualResponse}
                onChange={(e) => setManualResponse(e.target.value)}
                rows={3}
              />
              <Button 
                onClick={sendManualResponse} 
                disabled={!manualResponse.trim() || !isConnected}
                className="w-full"
              >
                <Send className="h-4 w-4 mr-2" />
                メッセージを送信
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>接続設定</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={testConnection} 
                className="w-full"
              >
                接続テスト
              </Button>
              <Button 
                onClick={disconnectWebSocket} 
                disabled={!isConnected}
                variant="outline"
                className="w-full"
              >
                切断
              </Button>
              
              <div className="text-sm text-gray-600">
                <p>接続状態: {isConnected ? '接続済み' : '切断中'}</p>
                <p>メッセージ数: {messages.length}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
} 