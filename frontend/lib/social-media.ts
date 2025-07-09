import axios from 'axios';

// Types for social media posts
interface SocialMediaPost {
  platform: 'twitter' | 'tiktok' | 'facebook' | 'instagram';
  content: string;
  image?: string;
  video?: string;
  hashtags?: string[];
  scheduledTime?: Date;
}

interface DisasterAlert {
  type: 'earthquake' | 'tsunami' | 'fire' | 'weather' | 'emergency';
  severity: 'low' | 'medium' | 'high' | 'critical';
  location: string;
  time: Date;
  details: string;
}

interface ProductPromotion {
  name: string;
  description: string;
  url: string;
  price?: string;
  category: 'emergency_kit' | 'food' | 'water' | 'medical' | 'communication' | 'shelter';
}

// Social Media Automation Service
export class SocialMediaAutomation {
  private static readonly PLATFORMS = {
    twitter: 'https://api.twitter.com/2/tweets',
    facebook: 'https://graph.facebook.com/v18.0/me/feed',
    instagram: 'https://graph.facebook.com/v18.0/me/media',
    tiktok: 'https://open-api.tiktok.com/share/video/upload/'
  };

  // 災害情報に基づく自動投稿
  static async postDisasterAlert(alert: DisasterAlert): Promise<void> {
    const content = this.generateDisasterContent(alert);
    
    // 各プラットフォームに同時投稿
    const posts: SocialMediaPost[] = [
      {
        platform: 'twitter',
        content: content.twitter,
        hashtags: ['#災害情報', '#緊急', '#安全確認', '#防災']
      },
      {
        platform: 'facebook',
        content: content.facebook,
        hashtags: ['災害情報', '緊急情報', '安全確認']
      },
      {
        platform: 'instagram',
        content: content.instagram,
        image: await this.generateDisasterImage(alert),
        hashtags: ['災害情報', '緊急情報', '防災', '安全確認']
      }
    ];

    await Promise.all(posts.map(post => this.publishToSocialMedia(post)));
  }

  // 防災グッズの自動宣伝投稿
  static async postProductPromotion(product: ProductPromotion): Promise<void> {
    const content = this.generateProductContent(product);
    
    const posts: SocialMediaPost[] = [
      {
        platform: 'twitter',
        content: content.twitter,
        hashtags: ['#防災グッズ', '#災害対策', '#備蓄', '#安全']
      },
      {
        platform: 'instagram',
        content: content.instagram,
        image: await this.generateProductImage(product),
        hashtags: ['防災グッズ', '災害対策', '備蓄', 'おすすめ商品']
      },
      {
        platform: 'facebook',
        content: content.facebook,
        hashtags: ['防災グッズ', '災害対策', '備蓄']
      }
    ];

    await Promise.all(posts.map(post => this.publishToSocialMedia(post)));
  }

  // YouTubeライブへの誘導投稿
  static async postYouTubeLivePromotion(videoId: string, topic: string): Promise<void> {
    const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
    
    const content = {
      twitter: `🔴 LIVE配信中！\n${topic}に関する最新情報をお届けしています。\n\n📺 ${youtubeUrl}\n\n#災害情報 #ライブ配信 #YouTube`,
      facebook: `現在ライブ配信中です！\n\n${topic}について、リアルタイムで最新情報をお伝えしています。ぜひご視聴ください。\n\n視聴はこちら: ${youtubeUrl}`,
      instagram: `📺 ライブ配信中 📺\n\n${topic}の最新情報をリアルタイムでお届け中です！\n\nYouTubeでライブ配信を行っています。ストーリーのリンクからご視聴ください。`,
      tiktok: `🚨 災害情報ライブ配信中 🚨\n\n${topic}について詳しく解説しています！\n\n#災害情報 #ライブ配信 #防災`
    };

    const posts: SocialMediaPost[] = [
      { platform: 'twitter', content: content.twitter },
      { platform: 'facebook', content: content.facebook },
      { platform: 'instagram', content: content.instagram },
      { platform: 'tiktok', content: content.tiktok }
    ];

    await Promise.all(posts.map(post => this.publishToSocialMedia(post)));
  }

  // 定期的な防災啓発投稿
  static async postEducationalContent(): Promise<void> {
    const tips = [
      {
        title: '緊急地震速報の活用',
        content: '緊急地震速報を受信したら、まず身の安全を確保しましょう。机の下に隠れる、頭を守るなどの行動を素早く取ることが重要です。',
        hashtags: ['緊急地震速報', '地震対策', '防災']
      },
      {
        title: '非常用持ち出し袋の準備',
        content: '災害時に最低3日間生活できる物資を準備しましょう。水、食料、懐中電灯、ラジオ、医薬品、重要書類のコピーなどが必要です。',
        hashtags: ['非常用持ち出し袋', '防災グッズ', '災害対策']
      },
      {
        title: '津波警報時の避難',
        content: '津波警報が発表されたら、高台や頑丈な高層建物へ避難しましょう。車での避難は渋滞の原因となるため、徒歩での避難が基本です。',
        hashtags: ['津波対策', '避難', '防災']
      }
    ];

    const randomTip = tips[Math.floor(Math.random() * tips.length)];
    
    const posts: SocialMediaPost[] = [
      {
        platform: 'twitter',
        content: `💡 防災豆知識\n\n${randomTip.title}\n\n${randomTip.content}`,
        hashtags: randomTip.hashtags
      },
      {
        platform: 'facebook',
        content: `【防災豆知識】${randomTip.title}\n\n${randomTip.content}\n\n日頃からの備えが大切です。皆さんも今一度、防災対策を見直してみてください。`,
        hashtags: randomTip.hashtags
      }
    ];

    await Promise.all(posts.map(post => this.publishToSocialMedia(post)));
  }

  // 実際のSNS投稿処理
  private static async publishToSocialMedia(post: SocialMediaPost): Promise<void> {
    try {
      switch (post.platform) {
        case 'twitter':
          await this.postToTwitter(post);
          break;
        case 'facebook':
          await this.postToFacebook(post);
          break;
        case 'instagram':
          await this.postToInstagram(post);
          break;
        case 'tiktok':
          await this.postToTikTok(post);
          break;
      }
      console.log(`${post.platform}への投稿が完了しました`);
    } catch (error) {
      console.error(`${post.platform}への投稿に失敗:`, error);
    }
  }

  // Twitter投稿
  private static async postToTwitter(post: SocialMediaPost): Promise<void> {
    const token = process.env.TWITTER_BEARER_TOKEN;
    if (!token) throw new Error('Twitter API token not configured');

    const tweetText = post.hashtags 
      ? `${post.content}\n\n${post.hashtags.map(tag => `#${tag}`).join(' ')}`
      : post.content;

    await axios.post(this.PLATFORMS.twitter, 
      { text: tweetText },
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
  }

  // Facebook投稿
  private static async postToFacebook(post: SocialMediaPost): Promise<void> {
    const token = process.env.FACEBOOK_ACCESS_TOKEN;
    if (!token) throw new Error('Facebook API token not configured');

    await axios.post(this.PLATFORMS.facebook, {
      message: post.content,
      access_token: token
    });
  }

  // Instagram投稿
  private static async postToInstagram(post: SocialMediaPost): Promise<void> {
    const token = process.env.INSTAGRAM_ACCESS_TOKEN;
    if (!token) throw new Error('Instagram API token not configured');

    // 画像付き投稿の場合
    if (post.image) {
      // まず画像をアップロード
      const mediaResponse = await axios.post(this.PLATFORMS.instagram, {
        image_url: post.image,
        caption: post.content,
        access_token: token
      });

      // 投稿を公開
      await axios.post(`https://graph.facebook.com/v18.0/me/media_publish`, {
        creation_id: mediaResponse.data.id,
        access_token: token
      });
    }
  }

  // TikTok投稿
  private static async postToTikTok(post: SocialMediaPost): Promise<void> {
    // TikTokは動画プラットフォームなので、動画コンテンツが必要
    console.log('TikTok投稿機能は動画コンテンツの準備が必要です');
  }

  // 災害情報コンテンツ生成
  private static generateDisasterContent(alert: DisasterAlert): any {
    const severityEmojis = {
      low: '⚠️',
      medium: '🚨',
      high: '🔴',
      critical: '🆘'
    };

    const emoji = severityEmojis[alert.severity];
    
    return {
      twitter: `${emoji} ${alert.type}情報\n\n場所: ${alert.location}\n時刻: ${alert.time.toLocaleString('ja-JP')}\n\n${alert.details}\n\n最新情報はYouTubeライブでご確認ください。`,
      facebook: `【${alert.type}情報】\n\n${emoji} 発生場所: ${alert.location}\n${emoji} 発生時刻: ${alert.time.toLocaleString('ja-JP')}\n\n詳細:\n${alert.details}\n\n引き続き安全にお気をつけください。最新情報はYouTubeライブ配信でお伝えしています。`,
      instagram: `${emoji} ${alert.type}情報 ${emoji}\n\n📍 ${alert.location}\n⏰ ${alert.time.toLocaleString('ja-JP')}\n\n${alert.details}\n\n皆様の安全をお祈りしています。`
    };
  }

  // 商品宣伝コンテンツ生成
  private static generateProductContent(product: ProductPromotion): any {
    const categoryEmojis = {
      emergency_kit: '🎒',
      food: '🍞',
      water: '💧',
      medical: '🩹',
      communication: '📱',
      shelter: '🏠'
    };

    const emoji = categoryEmojis[product.category];
    
    return {
      twitter: `${emoji} おすすめ防災グッズ\n\n${product.name}\n${product.description}\n\n${product.price ? `価格: ${product.price}` : ''}\n詳細: ${product.url}`,
      facebook: `【おすすめ防災グッズ】\n\n${emoji} ${product.name}\n\n${product.description}\n\n災害時の備えは日頃からが大切です。この機会にぜひご検討ください。\n\n${product.url}`,
      instagram: `${emoji} 防災グッズのご紹介 ${emoji}\n\n${product.name}\n\n${product.description}\n\n備えあれば憂いなし！\n詳細はプロフィールのリンクから✨`
    };
  }

  // 災害情報用画像生成（プレースホルダー）
  private static async generateDisasterImage(alert: DisasterAlert): Promise<string> {
    // 実際には画像生成AIまたは事前に用意した画像を使用
    return `https://via.placeholder.com/800x600/ff0000/ffffff?text=${encodeURIComponent(alert.type)}`;
  }

  // 商品用画像生成（プレースホルダー）
  private static async generateProductImage(product: ProductPromotion): Promise<string> {
    // 実際には商品画像または動的生成画像を使用
    return `https://via.placeholder.com/800x600/0066cc/ffffff?text=${encodeURIComponent(product.name)}`;
  }
}

// 投稿スケジューラー
export class PostScheduler {
  private static intervals: { [key: string]: NodeJS.Timeout } = {};

  static startScheduledPosts(): void {
    // 防災啓発投稿: 1時間ごと
    this.intervals.educational = setInterval(async () => {
      await SocialMediaAutomation.postEducationalContent();
    }, 3600000);

    // YouTubeライブ宣伝: 30分ごと
    this.intervals.youtubeLive = setInterval(async () => {
      const videoId = process.env.YOUTUBE_LIVE_VIDEO_ID;
      if (videoId) {
        await SocialMediaAutomation.postYouTubeLivePromotion(videoId, '災害情報ライブ配信');
      }
    }, 1800000);

    // 防災グッズ宣伝: 2時間ごと
    this.intervals.products = setInterval(async () => {
      const products = this.getRandomProducts();
      const randomProduct = products[Math.floor(Math.random() * products.length)];
      await SocialMediaAutomation.postProductPromotion(randomProduct);
    }, 7200000);
  }

  static stopScheduledPosts(): void {
    Object.values(this.intervals).forEach(interval => {
      clearInterval(interval);
    });
    this.intervals = {};
  }

  private static getRandomProducts(): ProductPromotion[] {
    return [
      {
        name: '防災リュック 30点セット',
        description: '地震・災害時に必要な防災グッズを厳選。家族4人が3日間過ごせる内容です。',
        url: 'https://example.com/emergency-kit',
        price: '¥9,800',
        category: 'emergency_kit'
      },
      {
        name: '長期保存水 2L×6本',
        description: '5年間保存可能な美味しい天然水。災害時の水分補給に最適です。',
        url: 'https://example.com/water',
        price: '¥1,980',
        category: 'water'
      },
      {
        name: '手回し充電ラジオライト',
        description: '停電時でも安心。手回し充電でラジオ・懐中電灯・スマホ充電が可能。',
        url: 'https://example.com/radio-light',
        price: '¥4,980',
        category: 'communication'
      }
    ];
  }
}

// AI コンテンツ生成器
export class AIContentGenerator {
  // OpenAI APIを使用してコンテンツを生成
  static async generateDisasterPost(disasterInfo: any): Promise<string> {
    try {
      const API_KEY = process.env.OPENAI_API_KEY;
      if (!API_KEY) return this.getFallbackContent(disasterInfo);

      const response = await axios.post('https://api.openai.com/v1/chat/completions', {
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: '日本の災害情報を分かりやすく、簡潔にまとめて投稿文を作成してください。不安を煽らず、正確な情報と適切な行動を促すトーンで書いてください。'
          },
          {
            role: 'user',
            content: `以下の災害情報についてSNS投稿文を作成してください：${JSON.stringify(disasterInfo)}`
          }
        ],
        max_tokens: 200,
        temperature: 0.7
      }, {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        }
      });

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('AI コンテンツ生成に失敗:', error);
      return this.getFallbackContent(disasterInfo);
    }
  }

  private static getFallbackContent(disasterInfo: any): string {
    return `災害情報をお知らせします。最新の情報はYouTubeライブ配信でご確認ください。皆様の安全をお祈りしています。`;
  }
} 