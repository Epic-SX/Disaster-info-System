"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { RefreshCw, Radio } from "lucide-react";
import { apiClient, API_ENDPOINTS } from "@/lib/api-config";

interface YouTubeLiveNewsListProps {
  className?: string;
  maxItems?: number;
}

interface BackendLiveStream {
  video_id: string;
  title: string;
  channel: string;
  description?: string;
  thumbnail?: string;
  link?: string;
  video_type?: string;
  verified_channel?: boolean;
}

interface YouTubeNewsArticle {
  id: string;
  videoId: string;
  title: string;
  channel: string;
  description: string;
  thumbnail: string;
  url: string;
  isLive: boolean;
  verified: boolean;
}

const FALLBACK_ARTICLES: YouTubeNewsArticle[] = [
  {
    id: "fallback-nhk",
    videoId: "jfKfPfyJRdk",
    title: "【速報】NHKニュース 防災ライブ",
    channel: "NHK",
    description: "全国の地震・災害情報をリアルタイムで配信",
    thumbnail: "/images/nhk-live-placeholder.svg",
    url: "https://www.youtube.com/watch?v=jfKfPfyJRdk",
    isLive: true,
    verified: true,
  },
  {
    id: "fallback-weathernews",
    videoId: "Ch_ZqaUQhc8",
    title: "ウェザーニュースLiVE 24時間放送",
    channel: "ウェザーニュース",
    description: "最新の気象・災害予測を随時速報",
    thumbnail: "/images/weathernews-live-placeholder.svg",
    url: "https://www.youtube.com/watch?v=Ch_ZqaUQhc8",
    isLive: true,
    verified: true,
  },
];

const YouTubeLiveNewsList = ({
  className = "",
  maxItems = 10,
}: YouTubeLiveNewsListProps) => {
  const [articles, setArticles] = useState<YouTubeNewsArticle[]>(FALLBACK_ARTICLES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const containerClass = useMemo(
    () =>
      [
        "h-full w-full bg-[#0a1929] text-white flex flex-col border border-gray-800/60 rounded-md",
        className,
      ]
        .filter(Boolean)
        .join(" "),
    [className]
  );

  const loadArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<{
        videos?: BackendLiveStream[];
        streams?: BackendLiveStream[];
      }>(`${API_ENDPOINTS.youtube.liveStreams}?location=Japan`);

      const list = response.videos || response.streams || [];

      if (list.length === 0) {
        setArticles(FALLBACK_ARTICLES);
      } else {
        const normalized = list.map<YouTubeNewsArticle>((item, index) => ({
          id: item.video_id || `live-${index}`,
          videoId: item.video_id,
          title: item.title,
          channel: item.channel,
          description:
            item.description?.slice(0, 80) ||
            "災害関連のライブ配信が進行中",
          thumbnail:
            item.thumbnail ||
            `https://img.youtube.com/vi/${item.video_id}/hqdefault.jpg`,
          url: item.link || `https://www.youtube.com/watch?v=${item.video_id}`,
          isLive: item.video_type === "live",
          verified: Boolean(item.verified_channel),
        }));
        setArticles(normalized.slice(0, maxItems));
      }

      setLastUpdated(
        new Date().toLocaleTimeString("ja-JP", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    } catch (err) {
      console.error("Failed to load YouTube live articles:", err);
      setError("最新の災害ライブ記事を取得できませんでした");
      setArticles(FALLBACK_ARTICLES);
    } finally {
      setLoading(false);
    }
  }, [maxItems]);

  useEffect(() => {
    loadArticles();
    const interval = setInterval(loadArticles, 60 * 1000);
    return () => clearInterval(interval);
  }, [loadArticles]);

  return (
    <div className={containerClass}>
      <div className="bg-[#1a2942] px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div>
          <div className="flex items-center gap-2 text-base font-bold">
            <Radio className="h-5 w-5 text-red-400" />
            災害ニュースライブ
          </div>
          <div className="text-xs text-gray-400">
            YouTubeライブからの速報記事一覧
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-300">
          {lastUpdated && (
            <span>更新 {lastUpdated}</span>
          )}
          <button
            onClick={loadArticles}
            className="p-2 rounded bg-white/10 hover:bg-white/20 transition-colors"
            title="最新のライブ記事を取得"
          >
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin text-blue-300" : ""}`}
            />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-gray-800">
        {loading && (
          <div className="p-6 text-center text-gray-400">読み込み中...</div>
        )}

        {!loading && error && (
          <div className="p-6 text-center text-red-400 text-sm">{error}</div>
        )}

        {!loading &&
          articles.map((article) => (
            <a
              key={article.id}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex gap-3 px-4 py-3 hover:bg-white/5 transition-colors"
            >
              <div className="relative w-32 h-20 rounded overflow-hidden bg-black/40 flex-shrink-0">
                <Image
                  src={article.thumbnail}
                  alt={article.title}
                  fill
                  sizes="128px"
                  className="object-cover"
                />
                {article.isLive && (
                  <span className="absolute top-1 left-1 bg-red-600 text-white text-[10px] font-bold px-2 py-[1px] rounded">
                    LIVE
                  </span>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-400 mb-1 flex items-center gap-2">
                  <span>{article.channel}</span>
                  {article.verified && (
                    <span className="text-blue-300 text-[10px] border border-blue-400/40 rounded px-1">
                      VERIFIED
                    </span>
                  )}
                </div>
                <div 
                  className="text-sm font-semibold leading-snug line-clamp-2"
                  title={article.title}
                >
                  {article.title}
                </div>
                <div className="text-xs text-gray-400 mt-1 line-clamp-2">
                  {article.description}
                </div>
              </div>
            </a>
          ))}

        {!loading && articles.length === 0 && (
          <div className="p-6 text-center text-gray-400 text-sm">
            表示できるライブ記事がありません
          </div>
        )}
      </div>
    </div>
  );
};

export default YouTubeLiveNewsList;

