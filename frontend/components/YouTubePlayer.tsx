"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize, 
  Camera,
  Users,
  MessageCircle,
  AlertCircle
} from 'lucide-react';

interface YouTubePlayerProps {
  videoId: string;
  title: string;
  autoplay?: boolean;
  muted?: boolean;
  controls?: boolean;
  loop?: boolean;
  className?: string;
}

export function YouTubePlayer({ 
  videoId, 
  title, 
  autoplay = true, 
  muted = true, 
  controls = false,
  loop = true,
  className = "" 
}: YouTubePlayerProps) {
  const playerRef = useRef<HTMLDivElement>(null);
  const [player, setPlayer] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(autoplay);
  const [isMuted, setIsMuted] = useState(muted);
  const [viewerCount, setViewerCount] = useState(0);
  const [isLive, setIsLive] = useState(false);
  const [apiLoadError, setApiLoadError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const checkIfLive = useCallback(async () => {
    try {
      // YouTube Data API で配信状況を確認
      const API_KEY = process.env.NEXT_PUBLIC_YOUTUBE_API_KEY;
      if (!API_KEY) return;

      const response = await fetch(
        `https://www.googleapis.com/youtube/v3/videos?id=${videoId}&part=liveStreamingDetails&key=${API_KEY}`
      );
      const data = await response.json();
      
      if (data.items && data.items[0]?.liveStreamingDetails) {
        setIsLive(true);
      }
    } catch (error) {
      console.error('ライブ状況の確認に失敗:', error);
    }
  }, [videoId]);

  const updateViewerCount = useCallback(async () => {
    try {
      const API_KEY = process.env.NEXT_PUBLIC_YOUTUBE_API_KEY;
      if (!API_KEY) return;

      const response = await fetch(
        `https://www.googleapis.com/youtube/v3/videos?id=${videoId}&part=liveStreamingDetails,statistics&key=${API_KEY}`
      );
      const data = await response.json();
      
      if (data.items && data.items[0]) {
        const concurrent = data.items[0].liveStreamingDetails?.concurrentViewers;
        const views = data.items[0].statistics?.viewCount;
        setViewerCount(parseInt(concurrent || views || '0'));
      }
    } catch (error) {
      console.error('視聴者数の取得に失敗:', error);
    }
  }, [videoId]);

  const onPlayerReady = useCallback((event: any) => {
    console.log('YouTube Player Ready');
    
    // ライブストリームの情報を取得
    checkIfLive();
    updateViewerCount();
    
    // 定期的に視聴者数を更新
    setInterval(updateViewerCount, 30000);
  }, [checkIfLive, updateViewerCount]);

  const onPlayerStateChange = useCallback((event: any) => {
    if (event.data === window.YT.PlayerState.PLAYING) {
      setIsPlaying(true);
    } else if (event.data === window.YT.PlayerState.PAUSED) {
      setIsPlaying(false);
    }
  }, []);

  const onPlayerError = useCallback((event: any) => {
    console.error('YouTube Player Error:', event.data);
  }, []);

  const initializePlayer = useCallback(() => {
    if (!playerRef.current) return;

    try {
      const newPlayer = new window.YT.Player(playerRef.current, {
        videoId: videoId,
        width: '100%',
        height: '100%',
        playerVars: {
          autoplay: autoplay ? 1 : 0,
          mute: muted ? 1 : 0,
          controls: controls ? 1 : 0,
          loop: loop ? 1 : 0,
          playlist: loop ? videoId : undefined,
          rel: 0,
          showinfo: 0,
          modestbranding: 1,
          fs: 1,
          cc_load_policy: 0,
          iv_load_policy: 3,
          autohide: 0
        },
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange,
          onError: onPlayerError
        }
      });

      setPlayer(newPlayer);
      setIsLoading(false);
    } catch (error) {
      console.error('Player initialization failed:', error);
      setApiLoadError(true);
      setIsLoading(false);
    }
  }, [videoId, autoplay, muted, controls, loop, onPlayerReady, onPlayerStateChange, onPlayerError]);

  const loadYouTubeAPI = useCallback(async () => {
    try {
      setIsLoading(true);
      setApiLoadError(false);

      // タイムアウト付きでYouTube APIを読み込み
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('YouTube API load timeout')), 10000);
      });

      const loadPromise = new Promise<void>((resolve, reject) => {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        tag.onload = () => resolve();
        tag.onerror = () => reject(new Error('Failed to load YouTube API'));
        
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

        window.onYouTubeIframeAPIReady = () => {
          resolve();
        };
      });

      await Promise.race([loadPromise, timeoutPromise]);
      
      // APIが読み込まれたら初期化
      if (window.YT) {
        initializePlayer();
      } else {
        // APIが読み込まれるまで待機
        setTimeout(() => {
          if (window.YT) {
            initializePlayer();
          } else {
            setApiLoadError(true);
            setIsLoading(false);
          }
        }, 2000);
      }
    } catch (error) {
      console.error('YouTube API load failed:', error);
      setApiLoadError(true);
      setIsLoading(false);
    }
  }, [initializePlayer]);

  useEffect(() => {
    // YouTube IFrame Player API の読み込み with error handling
    if (!window.YT) {
      loadYouTubeAPI();
    } else {
      initializePlayer();
    }

    return () => {
      if (player && player.destroy) {
        player.destroy();
      }
    };
  }, [videoId, loadYouTubeAPI, initializePlayer, player]);

  const togglePlayPause = () => {
    if (!player) return;

    if (isPlaying) {
      player.pauseVideo();
    } else {
      player.playVideo();
    }
  };

  const toggleMute = () => {
    if (!player) return;

    if (isMuted) {
      player.unMute();
      setIsMuted(false);
    } else {
      player.mute();
      setIsMuted(true);
    }
  };

  const enterFullscreen = () => {
    if (player && player.getIframe) {
      const iframe = player.getIframe();
      if (iframe.requestFullscreen) {
        iframe.requestFullscreen();
      }
    }
  };

  const retryLoadAPI = () => {
    setApiLoadError(false);
    loadYouTubeAPI();
  };

  // エラー状態またはAPIが利用できない場合のフォールバック表示
  if (apiLoadError) {
    return (
      <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-red-500" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg flex flex-col items-center justify-center text-white">
            <div className="text-center space-y-4">
              <div className="text-red-400">
                <Camera className="h-12 w-12 mx-auto mb-2" />
                YouTube API接続エラー
              </div>
              <p className="text-sm text-gray-300">
                YouTubeサーバーに接続できません。ネットワーク設定を確認してください。
              </p>
              <div className="space-y-2">
                <Button 
                  onClick={retryLoadAPI}
                  className="bg-red-600 hover:bg-red-700"
                >
                  再試行
                </Button>
                <div className="text-xs text-gray-400">
                  または{' '}
                  <a 
                    href={`https://www.youtube.com/watch?v=${videoId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline"
                  >
                    YouTubeで直接視聴
                  </a>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ローディング状態
  if (isLoading) {
    return (
      <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-blue-500 animate-pulse" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm">YouTube API読み込み中...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-green-500" />
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isLive && (
              <Badge className="bg-red-500 text-white animate-pulse">
                LIVE
              </Badge>
            )}
            {viewerCount > 0 && (
              <Badge variant="outline" className="text-white border-white/30">
                <Users className="h-3 w-3 mr-1" />
                {viewerCount.toLocaleString()}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
          <div ref={playerRef} className="w-full h-full" />
          
          {/* カスタムコントロール */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={togglePlayPause}
                  className="text-white hover:bg-white/20"
                >
                  {isPlaying ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
                
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={toggleMute}
                  className="text-white hover:bg-white/20"
                >
                  {isMuted ? (
                    <VolumeX className="h-4 w-4" />
                  ) : (
                    <Volume2 className="h-4 w-4" />
                  )}
                </Button>
              </div>
              
              <Button
                size="sm"
                variant="ghost"
                onClick={enterFullscreen}
                className="text-white hover:bg-white/20"
              >
                <Maximize className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        
        {/* 配信情報 */}
        <div className="mt-3 text-sm text-white/70">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Camera className="h-3 w-3" />
              24時間配信中
            </span>
            {isLive && (
              <span className="flex items-center gap-1">
                <MessageCircle className="h-3 w-3" />
                チャット分析中
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// 複数のライブカメラを管理するコンポーネント
interface LiveCameraGridProps {
  cameras: Array<{
    id: string;
    videoId: string;
    title: string;
    location: string;
  }>;
}

export function LiveCameraGrid({ cameras }: LiveCameraGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cameras.map((camera) => (
        <YouTubePlayer
          key={camera.id}
          videoId={camera.videoId}
          title={`${camera.title} - ${camera.location}`}
          autoplay={false}
          muted={true}
          controls={false}
          loop={true}
        />
      ))}
    </div>
  );
}

// YouTube Live Chat Component
interface YouTubeChatProps {
  videoId: string;
  height?: number;
}

export function YouTubeChat({ videoId, height = 400 }: YouTubeChatProps) {
  return (
    <Card className="bg-white/10 backdrop-blur-md border-white/20">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <MessageCircle className="h-5 w-5 text-blue-500" />
          ライブチャット
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div 
          className="w-full bg-white rounded-lg overflow-hidden"
          style={{ height: `${height}px` }}
        >
          <iframe
            src={`https://www.youtube.com/live_chat?v=${videoId}&embed_domain=${window.location.hostname}`}
            width="100%"
            height="100%"
            frameBorder="0"
            title="YouTube Live Chat"
          />
        </div>
      </CardContent>
    </Card>
  );
}

// Simple YouTube Player that only uses embed (most reliable)
export function YouTubePlayerSimple({ 
  videoId, 
  title, 
  autoplay = true, 
  muted = true,
  controls = true,
  className = "" 
}: YouTubePlayerProps) {
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [embedUrl, setEmbedUrl] = useState('');

  // Generate embed URL on client side to avoid hydration mismatch
  useEffect(() => {
    const url = `https://www.youtube-nocookie.com/embed/${videoId}?${new URLSearchParams({
      autoplay: autoplay ? '1' : '0',
      mute: muted ? '1' : '0',
      controls: controls ? '1' : '0',
      rel: '0',
      showinfo: '0',
      modestbranding: '1',
      fs: '1',
      cc_load_policy: '0',
      iv_load_policy: '3',
      origin: window.location.origin
    }).toString()}`;
    
    setEmbedUrl(url);
  }, [videoId, autoplay, muted, controls]);

  const handleLoad = () => {
    setIsLoading(false);
  };

  const handleError = () => {
    setHasError(true);
    setIsLoading(false);
  };

  if (hasError) {
    return (
      <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-red-500" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg flex flex-col items-center justify-center text-white">
            <div className="text-center space-y-4">
              <div className="text-red-400">
                <Camera className="h-12 w-12 mx-auto mb-2" />
                動画を読み込めません
              </div>
              <p className="text-sm text-gray-300">
                YouTubeへの接続が制限されている可能性があります
              </p>
              <a 
                href={`https://www.youtube.com/watch?v=${videoId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                YouTubeで視聴
              </a>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show loading until embedUrl is set to avoid hydration issues
  if (!embedUrl) {
    return (
      <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-blue-500 animate-pulse" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm">準備中...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-white flex items-center gap-2 text-sm">
          <Camera className="h-4 w-4 text-green-500" />
          {title}
          <Badge className="bg-blue-500 text-white text-xs ml-2">
            LIVE
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="relative aspect-video bg-gray-800 rounded-lg overflow-hidden">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-white text-center">
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                <p className="text-sm">動画読み込み中...</p>
              </div>
            </div>
          )}
          <iframe
            src={embedUrl}
            title={title}
            width="100%"
            height="100%"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            onLoad={handleLoad}
            onError={handleError}
            className="w-full h-full"
          />
        </div>
      </CardContent>
    </Card>
  );
}

// Alternative YouTube Player component for cases where IFrame API is blocked
interface YouTubeEmbedPlayerProps {
  videoId: string;
  autoplay?: boolean;
  muted?: boolean;
}

export function YouTubeEmbedPlayer({ 
  videoId, 
  autoplay = false, 
  muted = true 
}: YouTubeEmbedPlayerProps) {
  const [error, setError] = useState<string | null>(null);
  const [embedUrl, setEmbedUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!videoId) {
      setError('Video ID is required');
      setIsLoading(false);
      return;
    }

    try {
      // Use regular YouTube domain instead of youtube-nocookie.com for better reliability
      const params = new URLSearchParams({
        ...(autoplay && { autoplay: '1' }),
        ...(muted && { mute: '1' }),
        controls: '1',
        rel: '0',
        modestbranding: '1',
        iv_load_policy: '3'
      });

      const url = `https://www.youtube.com/embed/${videoId}?${params.toString()}`;
      setEmbedUrl(url);
      setError(null);
    } catch (err) {
      console.error('Error creating embed URL:', err);
      setError('Failed to create video URL');
    }
    
    setIsLoading(false);
  }, [videoId, autoplay, muted]);

  const handleIframeLoad = () => {
    setIsLoading(false);
  };

  const handleIframeError = () => {
    setError('Failed to load video player');
    setIsLoading(false);
  };

  if (error) {
    return (
      <Card className="aspect-video bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
        <div className="text-center text-gray-500 dark:text-gray-400 p-4">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">動画の読み込みに失敗しました</p>
          <p className="text-xs mt-1">{error}</p>
          <button 
            onClick={() => window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank')}
            className="mt-2 text-blue-500 hover:text-blue-700 text-xs underline"
          >
            YouTubeで視聴する
          </button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden relative">
      {isLoading && (
        <div className="absolute inset-0 bg-gray-100 dark:bg-gray-800 flex items-center justify-center z-10">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-500 mx-auto mb-2"></div>
            <p className="text-sm">動画を読み込み中...</p>
          </div>
        </div>
      )}
      {embedUrl && (
        <iframe
          src={embedUrl}
          className="w-full aspect-video"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          onLoad={handleIframeLoad}
          onError={handleIframeError}
          title="YouTube Video Player"
        />
      )}
    </Card>
  );
}

// Hybrid component that tries IFrame API first, then falls back to embed
export function YouTubePlayerHybrid(props: YouTubePlayerProps) {
  const [useEmbed, setUseEmbed] = useState(true); // Default to embed for better reliability
  const [apiAttempted, setApiAttempted] = useState(false);

  useEffect(() => {
    // For now, always use embed to avoid connectivity issues
    // TODO: Add better detection mechanism or user preference
    setApiAttempted(true);
    setUseEmbed(true);
    
    // Commented out the API test for now since it's not reliable
    // const testYouTubeAccess = async () => {
    //   try {
    //     const controller = new AbortController();
    //     const timeoutId = setTimeout(() => controller.abort(), 5000);

    //     await fetch('https://www.youtube.com/iframe_api', {
    //       method: 'HEAD',
    //       signal: controller.signal
    //     });

    //     clearTimeout(timeoutId);
    //     setApiAttempted(true);
    //   } catch (error) {
    //     console.log('YouTube IFrame API not accessible, using embed fallback');
    //     setUseEmbed(true);
    //     setApiAttempted(true);
    //   }
    // };

    // testYouTubeAccess();
  }, []);

  // Show loading until we determine which method to use
  if (!apiAttempted) {
    return (
      <Card className={`bg-white/10 backdrop-blur-md border-white/20 ${props.className}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-white flex items-center gap-2 text-sm">
            <Camera className="h-4 w-4 text-blue-500 animate-pulse" />
            {props.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm">接続確認中...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Use embed player if API is not accessible
  if (useEmbed) {
    return <YouTubeEmbedPlayer {...props} />;
  }

  // Use regular player with API
  return <YouTubePlayer {...props} />;
}

// 外部環境変数の型定義を追加
declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady: () => void;
  }
} 