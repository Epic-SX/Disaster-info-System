// YouTube Player Configuration
export const YOUTUBE_CONFIG = {
  // Fallback settings
  enableAPIFallback: true,
  enableEmbedFallback: true,
  useHybridByDefault: true,
  
  // Timeout settings
  apiLoadTimeout: 10000, // 10 seconds
  connectivityTestTimeout: 5000, // 5 seconds
  
  // Player defaults
  defaultPlayerVars: {
    autoplay: 1,
    mute: 1,
    controls: 1,
    rel: 0,
    showinfo: 0,
    modestbranding: 1,
    fs: 1,
    cc_load_policy: 0,
    iv_load_policy: 3,
    autohide: 0
  },
  
  // Alternative domains for regions where YouTube is blocked
  alternativeDomains: [
    'www.youtube-nocookie.com',
    'www.youtube.com'
  ],
  
  // Error messages
  errorMessages: {
    apiTimeout: 'YouTube API読み込みがタイムアウトしました',
    connectionFailed: 'YouTubeサーバーに接続できません',
    embedFailed: '動画を読み込めません',
    generalError: '予期しないエラーが発生しました'
  }
};

export type YouTubePlayerMode = 'api' | 'embed' | 'hybrid' | 'auto';

export const getEmbedUrl = (videoId: string, params: Record<string, string | number> = {}) => {
  const domain = YOUTUBE_CONFIG.alternativeDomains[0]; // Use nocookie domain by default
  const urlParams = new URLSearchParams();
  
  // Add default params
  Object.entries(YOUTUBE_CONFIG.defaultPlayerVars).forEach(([key, value]) => {
    urlParams.append(key, value.toString());
  });
  
  // Override with custom params
  Object.entries(params).forEach(([key, value]) => {
    urlParams.set(key, value.toString());
  });
  
  // Add origin for security
  if (typeof window !== 'undefined') {
    urlParams.set('origin', window.location.origin);
  }
  
  return `https://${domain}/embed/${videoId}?${urlParams.toString()}`;
};

// Test if YouTube is accessible
export const testYouTubeConnectivity = async (): Promise<boolean> => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), YOUTUBE_CONFIG.connectivityTestTimeout);

    await fetch('https://www.youtube.com/iframe_api', {
      method: 'HEAD',
      signal: controller.signal,
      mode: 'no-cors' // Avoid CORS issues
    });

    clearTimeout(timeoutId);
    return true;
  } catch (error) {
    console.log('YouTube connectivity test failed:', error);
    return false;
  }
};

// Get the best player mode based on connectivity
export const getBestPlayerMode = async (): Promise<YouTubePlayerMode> => {
  if (!YOUTUBE_CONFIG.useHybridByDefault) {
    return 'api';
  }
  
  const isAccessible = await testYouTubeConnectivity();
  return isAccessible ? 'api' : 'embed';
}; 