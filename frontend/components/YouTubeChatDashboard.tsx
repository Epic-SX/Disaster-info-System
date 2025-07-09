'use client';

import React, { useState, useEffect, useRef } from 'react';
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
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'reconnecting'>('disconnected');
  const [manualResponse, setManualResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket connection
  useEffect(() => {
    // Delay initial connection slightly to ensure backend is ready
    const connectTimer = setTimeout(() => {
      connectWebSocket();
    }, 1000);
    
    fetchInitialData();
    
    return () => {
      clearTimeout(connectTimer);
      if (wsRef.current) {
        console.log('🧹 Cleaning up WebSocket connection');
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const testConnection = async () => {
    console.log('🧪 Testing WebSocket connection...');
    setError(null);
    
    try {
      // First test if the backend is reachable
      const healthResponse = await fetch('http://localhost:8000/api/health');
      if (!healthResponse.ok) {
        setError('Backend server not responding');
        return;
      }
      
      const healthData = await healthResponse.json();
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

  const connectWebSocket = () => {
    // Prevent multiple simultaneous connection attempts
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      console.log('⏳ WebSocket connection already in progress...');
      return;
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      // Add connection state logging
      console.log('🚀 Attempting to connect to WebSocket at ws://localhost:8000/ws');
      setError(null);
      
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      // Set a connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.log('⏰ WebSocket connection timeout');
          ws.close();
          setError('Connection timeout');
        }
      }, 5000);
      
      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        setIsConnected(true);
        setError(null);
        console.log('✅ WebSocket connected successfully');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 Received WebSocket message:', data);
          
          if (data.type === 'chat_message') {
            setMessages(prev => [...prev, data.message].slice(-100)); // Keep last 100 messages
          } else if (data.type === 'analytics_update') {
            setAnalytics(data.analytics);
          } else if (data.type === 'ping') {
            // Keep-alive ping
            console.log('🏓 Received ping from server');
          } else if (data.type === 'connection_established') {
            console.log('🎯 Connection established:', data.message);
          }
        } catch (parseError) {
          console.error('Error parsing WebSocket message:', parseError);
        }
      };
      
      ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        setIsConnected(false);
        
        // More detailed close code handling
        const closeReason = event.code === 1006 ? 'Connection lost unexpectedly' :
                          event.code === 1000 ? 'Normal closure' :
                          event.code === 1001 ? 'Endpoint going away' :
                          event.code === 1002 ? 'Protocol error' :
                          event.code === 1003 ? 'Unsupported data' :
                          event.reason || 'Unknown reason';
        
        console.log(`🔌 WebSocket disconnected. Code: ${event.code}, Reason: ${closeReason}`);
        
        // Only attempt to reconnect for unexpected disconnections
        if (event.code === 1006 || (event.code !== 1000 && event.code !== 1001)) {
          console.log('🔄 Attempting to reconnect in 3 seconds...');
          setTimeout(connectWebSocket, 3000);
        }
      };
      
      ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('❌ WebSocket error occurred');
        console.error('WebSocket readyState:', ws.readyState);
        console.error('WebSocket URL:', ws.url);
        
        // Don't set connection error immediately, wait to see if it recovers
        if (ws.readyState === WebSocket.CLOSED) {
          setError('WebSocket connection failed');
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      setError('Failed to create WebSocket connection');
      console.error('💥 WebSocket connection creation failed:', error);
    }
  };

  const fetchInitialData = async () => {
    setIsLoading(true);
    try {
      // Fetch recent messages
      const messagesResponse = await fetch('http://localhost:8000/api/chat/messages?limit=50');
      if (messagesResponse.ok) {
        const messagesData = await messagesResponse.json();
        setMessages(messagesData);
      }

      // Fetch analytics
      const analyticsResponse = await fetch('http://localhost:8000/api/chat/analytics');
      if (analyticsResponse.ok) {
        const analyticsData = await analyticsResponse.json();
        setAnalytics(analyticsData);
      }

      // Fetch auto-responses
      const responsesResponse = await fetch('http://localhost:8000/api/chat/responses');
      if (responsesResponse.ok) {
        const responsesData = await responsesResponse.json();
        setAutoResponses(responsesData);
      }
    } catch (error) {
      setError('Failed to fetch initial data');
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendManualResponse = async () => {
    if (!manualResponse.trim()) return;
    
    try {
      const response = await fetch('http://localhost:8000/api/chat/response', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: manualResponse }),
      });
      
      if (response.ok) {
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
      } else {
        setError('Failed to send message');
      }
    } catch (error) {
      setError('Network error while sending message');
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
      <Alert className={isConnected ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
        <Activity className={`h-4 w-4 ${isConnected ? 'text-green-600' : 'text-red-600'}`} />
        <AlertDescription>
          チャットサービスの状態: <strong>
            {connectionStatus === 'connected' ? '接続済み' : 
             connectionStatus === 'connecting' ? '接続中...' :
             connectionStatus === 'reconnecting' ? '再接続中...' :
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