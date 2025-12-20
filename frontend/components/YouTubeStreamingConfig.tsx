"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { apiClient } from '@/lib/api-config';
import { 
  Radio, 
  Circle,
  Settings,
  Youtube,
  PlayCircle,
  StopCircle,
  AlertTriangle,
  CheckCircle,
  Info,
  Copy,
  ExternalLink
} from 'lucide-react';

interface StreamingStatus {
  is_streaming: boolean;
  dashboard_url: string;
  stream_url: string;
  resolution: string;
  framerate: number;
  video_bitrate: string;
  process_alive: boolean;
}

interface StreamConfig {
  stream_key: string;
  stream_url: string;
  dashboard_url: string;
}

export function YouTubeStreamingConfig() {
  const [streamKey, setStreamKey] = useState('');
  const [streamUrl, setStreamUrl] = useState('rtmp://a.rtmp.youtube.com/live2');
  const [dashboardUrl, setDashboardUrl] = useState('http://49.212.176.130/');
  const [status, setStatus] = useState<StreamingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [configSaved, setConfigSaved] = useState(false);

  // Load streaming status on component mount
  useEffect(() => {
    loadStreamingStatus();
    // Load saved configuration
    loadSavedConfig();
    // Poll status every 5 seconds
    const interval = setInterval(loadStreamingStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadSavedConfig = () => {
    // Load from localStorage
    const saved = localStorage.getItem('youtube_stream_config');
    if (saved) {
      try {
        const config: StreamConfig = JSON.parse(saved);
        setStreamKey(config.stream_key || '');
        setStreamUrl(config.stream_url || 'rtmp://a.rtmp.youtube.com/live2');
        setDashboardUrl(config.dashboard_url || 'http://49.212.176.130/');
        setConfigSaved(true);
      } catch (e) {
        console.error('Failed to load saved config:', e);
      }
    }
  };

  const saveConfig = () => {
    const config: StreamConfig = {
      stream_key: streamKey,
      stream_url: streamUrl,
      dashboard_url: dashboardUrl
    };
    localStorage.setItem('youtube_stream_config', JSON.stringify(config));
    setConfigSaved(true);
    setSuccess('配信設定を保存しました');
    setTimeout(() => setSuccess(''), 3000);
  };

  const loadStreamingStatus = async () => {
    try {
      const response = await apiClient.get<StreamingStatus>('/api/streaming/status');
      setStatus(response);
    } catch (err) {
      console.error('Error loading streaming status:', err);
    }
  };

  const startStreaming = async () => {
    if (!streamKey) {
      setError('ストリームキーを入力してください');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await apiClient.post(
        `/api/streaming/start?stream_key=${encodeURIComponent(streamKey)}`
      );
      
      setSuccess('YouTube Liveへの配信を開始しました！');
      await loadStreamingStatus();
      
      // Save the configuration on successful start
      saveConfig();
    } catch (err: any) {
      console.error('Error starting stream:', err);
      
      // Handle detailed error messages from backend
      let errorMessage = 'ストリーミングの開始に失敗しました';
      
      if (err.message && err.message.includes('503')) {
        errorMessage = '必要な依存関係が不足しています。サーバーにFFmpegとXvfbをインストールしてください。\n\nインストール方法:\nsudo apt-get install -y ffmpeg xvfb\n\nインストール後、バックエンドを再起動してください:\npm2 restart disaster-backend';
      } else if (err.response?.data?.detail) {
        // Handle detailed error from backend
        if (typeof err.response.data.detail === 'object') {
          errorMessage = err.response.data.detail.message || err.response.data.detail.solution || errorMessage;
        } else {
          errorMessage = err.response.data.detail;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const stopStreaming = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await apiClient.post('/api/streaming/stop');
      setSuccess('配信を停止しました');
      await loadStreamingStatus();
    } catch (err: any) {
      console.error('Error stopping stream:', err);
      setError(err.response?.data?.detail || '配信の停止に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('クリップボードにコピーしました');
    setTimeout(() => setSuccess(''), 2000);
  };

  const getStatusBadge = () => {
    if (!status) {
      return <Badge variant="outline">読み込み中...</Badge>;
    }
    
    if (status.is_streaming && status.process_alive) {
      return (
        <Badge className="bg-red-500 text-white animate-pulse">
          <Radio className="h-3 w-3 mr-1" />
          配信中
        </Badge>
      );
    } else if (status.is_streaming && !status.process_alive) {
      return (
        <Badge className="bg-yellow-500 text-white">
          <AlertTriangle className="h-3 w-3 mr-1" />
          エラー
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary">
          <Circle className="h-3 w-3 mr-1" />
          停止中
        </Badge>
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Youtube className="h-5 w-5 text-red-500" />
                YouTube Live 配信設定
              </CardTitle>
              <CardDescription>
                災害情報ダッシュボードをYouTube Liveで配信します
              </CardDescription>
            </div>
            {getStatusBadge()}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Success/Error Messages */}
          {success && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-800">成功</AlertTitle>
              <AlertDescription className="text-green-700">{success}</AlertDescription>
            </Alert>
          )}
          
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>エラー</AlertTitle>
              <AlertDescription className="whitespace-pre-wrap">{error}</AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="config" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="config">配信設定</TabsTrigger>
              <TabsTrigger value="status">ステータス</TabsTrigger>
              <TabsTrigger value="help">使い方</TabsTrigger>
            </TabsList>

            {/* Configuration Tab */}
            <TabsContent value="config" className="space-y-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="stream-key">ストリームキー *</Label>
                  <div className="flex gap-2">
                    <Input
                      id="stream-key"
                      type="password"
                      placeholder="xxxx-xxxx-xxxx-xxxx-xxxx"
                      value={streamKey}
                      onChange={(e) => setStreamKey(e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      size="icon"
                      variant="outline"
                      onClick={() => copyToClipboard(streamKey)}
                      disabled={!streamKey}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    YouTube Studioの「ライブ配信」セクションで取得できます
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="stream-url">ストリームURL</Label>
                  <div className="flex gap-2">
                    <Input
                      id="stream-url"
                      type="text"
                      value={streamUrl}
                      onChange={(e) => setStreamUrl(e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      size="icon"
                      variant="outline"
                      onClick={() => copyToClipboard(streamUrl)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    通常は変更不要です（デフォルト: rtmp://a.rtmp.youtube.com/live2）
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dashboard-url">ダッシュボードURL</Label>
                  <div className="flex gap-2">
                    <Input
                      id="dashboard-url"
                      type="text"
                      value={dashboardUrl}
                      onChange={(e) => setDashboardUrl(e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      size="icon"
                      variant="outline"
                      onClick={() => window.open(dashboardUrl, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    配信するダッシュボードのURL
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={saveConfig}
                    variant="outline"
                    disabled={!streamKey}
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    設定を保存
                  </Button>
                </div>

                <div className="pt-4 border-t">
                  <div className="flex gap-2">
                    {!status?.is_streaming ? (
                      <Button
                        onClick={startStreaming}
                        disabled={loading || !streamKey}
                        className="bg-red-600 hover:bg-red-700 text-white"
                      >
                        <PlayCircle className="mr-2 h-4 w-4" />
                        {loading ? '開始中...' : '配信を開始'}
                      </Button>
                    ) : (
                      <Button
                        onClick={stopStreaming}
                        disabled={loading}
                        variant="destructive"
                      >
                        <StopCircle className="mr-2 h-4 w-4" />
                        {loading ? '停止中...' : '配信を停止'}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Status Tab */}
            <TabsContent value="status" className="space-y-4">
              {status ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">配信状態</Label>
                      <p className="font-medium">
                        {status.is_streaming ? '配信中' : '停止中'}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">プロセス状態</Label>
                      <p className="font-medium">
                        {status.process_alive ? '実行中' : '停止'}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">解像度</Label>
                      <p className="font-medium">{status.resolution}</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">フレームレート</Label>
                      <p className="font-medium">{status.framerate} fps</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">ビットレート</Label>
                      <p className="font-medium">{status.video_bitrate}</p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">配信URL</Label>
                      <p className="font-medium text-xs truncate">{status.stream_url}</p>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-sm text-muted-foreground">ダッシュボードURL</Label>
                    <p className="font-medium text-xs break-all">{status.dashboard_url}</p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  ステータス情報を読み込んでいます...
                </div>
              )}
            </TabsContent>

            {/* Help Tab */}
            <TabsContent value="help" className="space-y-4">
              <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle>YouTube Live配信の手順</AlertTitle>
                <AlertDescription className="space-y-2 mt-2">
                  <ol className="list-decimal list-inside space-y-2">
                    <li>
                      <a 
                        href="https://studio.youtube.com" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        YouTube Studio
                      </a>
                      にアクセス
                    </li>
                    <li>左メニューから「ライブ配信」を選択</li>
                    <li>「ストリームキー」をコピー</li>
                    <li>このページの「配信設定」タブにストリームキーを貼り付け</li>
                    <li>「配信を開始」ボタンをクリック</li>
                    <li>YouTube Studioで配信が開始されたことを確認</li>
                  </ol>
                </AlertDescription>
              </Alert>

              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>注意事項</AlertTitle>
                <AlertDescription className="space-y-1 mt-2">
                  <ul className="list-disc list-inside space-y-1">
                    <li>配信にはFFmpegが必要です</li>
                    <li>サーバーに十分なリソース（CPU/メモリ/帯域）が必要です</li>
                    <li>ストリームキーは他人に公開しないでください</li>
                    <li>配信開始まで数秒〜数十秒かかる場合があります</li>
                  </ul>
                </AlertDescription>
              </Alert>

              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-medium mb-2">提供されたストリーム情報</h4>
                <div className="space-y-2 text-sm font-mono">
                  <div>
                    <span className="text-muted-foreground">ストリームキー:</span>
                    <p className="bg-background p-2 rounded mt-1">4dzh-z5y1-69km-gw0u-0342</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">ストリームURL:</span>
                    <p className="bg-background p-2 rounded mt-1">rtmp://a.rtmp.youtube.com/live2</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setStreamKey('4dzh-z5y1-69km-gw0u-0342');
                    setStreamUrl('rtmp://a.rtmp.youtube.com/live2');
                    setSuccess('ストリーム情報を入力しました');
                  }}
                  className="mt-2"
                >
                  この情報を使用
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

export default YouTubeStreamingConfig;


