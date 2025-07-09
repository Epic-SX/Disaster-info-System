import axios from 'axios';

// Types for API responses
export interface P2PQuakeData {
  issue: {
    time: string;
    type: string;
    source: string;
  };
  earthquake?: {
    time: string;
    hypocenter: {
      name: string;
      latitude: number;
      longitude: number;
      depth: number;
    };
    maxScale: number;
    domesticTsunami: string;
  };
  details?: {
    text: string;
  };
}

export interface JMAData {
  title: string;
  link: string;
  description: string;
  pubDate: string;
  category: string;
}

// P2P地震情報API
export class DisasterAPI {
  private static readonly P2P_BASE_URL = 'https://api.p2pquake.net/v2/history';
  private static readonly JMA_BASE_URL = 'https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml';

  // 地震情報を取得
  static async getEarthquakeInfo(): Promise<P2PQuakeData[]> {
    try {
      const response = await axios.get(`${this.P2P_BASE_URL}?codes=551&limit=10`, {
        headers: {
          'Accept': 'application/json',
        }
      });
      return response.data;
    } catch (error) {
      console.error('地震情報の取得に失敗:', error);
      return [];
    }
  }

  // 津波情報を取得
  static async getTsunamiInfo(): Promise<P2PQuakeData[]> {
    try {
      const response = await axios.get(`${this.P2P_BASE_URL}?codes=552&limit=10`, {
        headers: {
          'Accept': 'application/json',
        }
      });
      return response.data;
    } catch (error) {
      console.error('津波情報の取得に失敗:', error);
      return [];
    }
  }

  // 緊急地震速報を取得
  static async getEEWInfo(): Promise<P2PQuakeData[]> {
    try {
      const response = await axios.get(`${this.P2P_BASE_URL}?codes=556&limit=5`, {
        headers: {
          'Accept': 'application/json',
        }
      });
      return response.data;
    } catch (error) {
      console.error('緊急地震速報の取得に失敗:', error);
      return [];
    }
  }

  // 気象情報（風情報含む）を取得
  static async getWeatherInfo(lat: number, lon: number): Promise<any> {
    try {
      // OpenWeatherMap API (要API キー)
      const API_KEY = process.env.NEXT_PUBLIC_OPENWEATHER_API_KEY;
      if (!API_KEY) {
        console.warn('OpenWeatherMap API キーが設定されていません');
        return null;
      }

      const response = await axios.get(
        `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${API_KEY}&units=metric&lang=ja`
      );
      return response.data;
    } catch (error) {
      console.error('気象情報の取得に失敗:', error);
      return null;
    }
  }

  // ニュース情報を取得（RSS）
  static async getDisasterNews(): Promise<any[]> {
    try {
      // RSS to JSON conversion service
      const rssUrl = 'https://www3.nhk.or.jp/rss/news/cat0.xml'; // NHK 社会ニュース
      const response = await axios.get(
        `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(rssUrl)}&count=10`
      );
      return response.data.items || [];
    } catch (error) {
      console.error('ニュース情報の取得に失敗:', error);
      return [];
    }
  }

  // 火災情報を取得（模擬）
  static async getFireInfo(): Promise<any[]> {
    try {
      // 実際には火災情報APIまたはWebスクレイピングを実装
      // ここでは模擬データを返す
      return [
        {
          id: 1,
          location: '東京都新宿区',
          latitude: 35.6938,
          longitude: 139.7036,
          intensity: 'medium',
          time: new Date().toISOString(),
          description: '建物火災'
        }
      ];
    } catch (error) {
      console.error('火災情報の取得に失敗:', error);
      return [];
    }
  }
}

// YouTube Live Chat API (pytchatの代替としてWebSocket経由)
export class YouTubeChatAPI {
  private static ws: WebSocket | null = null;

  static connectToChat(videoId: string): WebSocket | null {
    try {
      // WebSocket経由でYouTube Live Chatに接続
      // 実際の実装では認証とAPIキーが必要
      this.ws = new WebSocket(`wss://your-websocket-server.com/youtube-chat/${videoId}`);
      
      this.ws.onopen = () => {
        console.log('YouTube Live Chat に接続しました');
      };

      this.ws.onmessage = (event) => {
        const chatData = JSON.parse(event.data);
        this.processChatMessage(chatData);
      };

      this.ws.onerror = (error) => {
        console.error('YouTube Chat接続エラー:', error);
      };

      return this.ws;
    } catch (error) {
      console.error('YouTube Chat接続に失敗:', error);
      return null;
    }
  }

  private static processChatMessage(chatData: any) {
    // チャットメッセージの分析とAI応答の実装
    console.log('新しいチャットメッセージ:', chatData);
    
    // キーワード分析
    const message = chatData.message?.toLowerCase() || '';
    
    if (message.includes('防災') || message.includes('地震') || message.includes('津波')) {
      this.sendAutoResponse('disaster');
    } else if (message.includes('グッズ') || message.includes('準備')) {
      this.sendAutoResponse('goods');
    }
  }

  private static sendAutoResponse(type: string) {
    const responses: { [key: string]: string[] } = {
      disaster: [
        '🚨 緊急時は身の安全を最優先に！',
        '📱 緊急地震速報アプリの設定をお忘れなく',
        '⚠️ 避難場所の確認をしておきましょう'
      ],
      goods: [
        '🎒 防災グッズリスト: https://example.com/goods',
        '💡 懐中電灯、ラジオ、水、非常食をご準備ください',
        '🔋 モバイルバッテリーも忘れずに！'
      ]
    };

    const messageList = responses[type] || [];
    const randomMessage = messageList[Math.floor(Math.random() * messageList.length)];
    
    // 実際にはYouTube Chat APIを通じてメッセージを送信
    console.log('自動応答:', randomMessage);
  }

  static disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// 地図データ用のユーティリティ
export class MapUtils {
  // 地震の震度を色に変換
  static getIntensityColor(intensity: number): string {
    if (intensity >= 7) return '#8B0000'; // 震度7: 濃い赤
    if (intensity >= 6) return '#FF0000'; // 震度6: 赤
    if (intensity >= 5) return '#FF6600'; // 震度5: オレンジ
    if (intensity >= 4) return '#FFFF00'; // 震度4: 黄色
    if (intensity >= 3) return '#00FF00'; // 震度3: 緑
    if (intensity >= 2) return '#00FFFF'; // 震度2: 水色
    return '#0000FF'; // 震度1: 青
  }

  // 風速を色に変換
  static getWindSpeedColor(speed: number): string {
    if (speed >= 25) return '#8B0000'; // 暴風
    if (speed >= 17) return '#FF0000'; // 強風
    if (speed >= 10) return '#FF6600'; // やや強い風
    if (speed >= 5) return '#FFFF00';  // 弱い風
    return '#00FF00'; // 微風
  }

  // 火災の強度を色に変換
  static getFireIntensityColor(intensity: string): string {
    switch (intensity) {
      case 'high': return '#8B0000';
      case 'medium': return '#FF6600';
      case 'low': return '#FFFF00';
      default: return '#00FF00';
    }
  }
}

// データの定期更新管理
export class DataUpdateManager {
  private static intervals: { [key: string]: NodeJS.Timeout } = {};

  static startPeriodicUpdates(callbacks: {
    onEarthquakeUpdate?: (data: any[]) => void;
    onTsunamiUpdate?: (data: any[]) => void;
    onNewsUpdate?: (data: any[]) => void;
    onWeatherUpdate?: (data: any) => void;
  }) {
    // 地震情報: 30秒ごと
    this.intervals.earthquake = setInterval(async () => {
      if (callbacks.onEarthquakeUpdate) {
        const data = await DisasterAPI.getEarthquakeInfo();
        callbacks.onEarthquakeUpdate(data);
      }
    }, 30000);

    // 津波情報: 1分ごと
    this.intervals.tsunami = setInterval(async () => {
      if (callbacks.onTsunamiUpdate) {
        const data = await DisasterAPI.getTsunamiInfo();
        callbacks.onTsunamiUpdate(data);
      }
    }, 60000);

    // ニュース: 5分ごと
    this.intervals.news = setInterval(async () => {
      if (callbacks.onNewsUpdate) {
        const data = await DisasterAPI.getDisasterNews();
        callbacks.onNewsUpdate(data);
      }
    }, 300000);

    // 気象情報: 10分ごと
    this.intervals.weather = setInterval(async () => {
      if (callbacks.onWeatherUpdate) {
        // 東京の座標
        const data = await DisasterAPI.getWeatherInfo(35.6762, 139.6503);
        callbacks.onWeatherUpdate(data);
      }
    }, 600000);
  }

  static stopPeriodicUpdates() {
    Object.values(this.intervals).forEach(interval => {
      clearInterval(interval);
    });
    this.intervals = {};
  }
} 