"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import Hls from 'hls.js';
import { apiClient, API_ENDPOINTS, API_BASE_URL } from '@/lib/api-config';

type CameraFeed = {
  id: string;
  name: string;
  status: string;
  location: string;
  stream_url?: string | null;
  thumbnail_url?: string | null;
  last_updated: string | Date;
  coordinates?: {
    lat: number;
    lng: number;
  } | null;
};

type TsunamiAlert = {
  id: string;
  location: string;
  level: string;
  time: string;
};

const JAPAN_CENTER = { lat: 36.2, lng: 138.0 };
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const TSUNAMI_LEVEL_PRIORITY: Record<string, number> = {
  warning: 3,
  advisory: 2,
  watch: 1,
  information: 0,
};

const levelColorMap: Record<string, string> = {
  warning: 'text-red-400 border-red-500/60',
  advisory: 'text-amber-300 border-amber-400/60',
  watch: 'text-emerald-300 border-emerald-400/60',
  information: 'text-slate-300 border-slate-500/60',
};

// Ensure Leaflet default icons render inside Next.js
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: '/leaflet/marker-icon-2x.png',
    iconUrl: '/leaflet/marker-icon.png',
    shadowUrl: '/leaflet/marker-shadow.png',
  });
}

const createLabelIcon = (label: string, active: boolean) => {
  return L.divIcon({
    className: '',
    html: `<div class="px-2 py-1 rounded-full text-xs font-semibold ${
      active ? 'bg-emerald-500 text-white' : 'bg-white/90 text-slate-800'
    } shadow-lg border border-white/70 whitespace-nowrap">${label}</div>`,
    iconSize: [label.length * 8 + 32, 24],
    iconAnchor: [((label.length * 8 + 32) / 2), 24],
  });
};

const CoastGuardCameraPanel: React.FC = () => {
  const [cameraFeeds, setCameraFeeds] = useState<CameraFeed[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<CameraFeed | null>(null);
  const [tsunamiAlerts, setTsunamiAlerts] = useState<TsunamiAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsRef = useRef<Hls | null>(null);

  const camerasWithCoordinates = useMemo(
    () => cameraFeeds.filter((camera) => camera.coordinates?.lat && camera.coordinates?.lng),
    [cameraFeeds]
  );

  const camerasWithoutCoordinates = useMemo(
    () => cameraFeeds.filter((camera) => !camera.coordinates?.lat || !camera.coordinates?.lng),
    [cameraFeeds]
  );

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        setIsLoading(true);
        const data = await apiClient.get<CameraFeed[]>(API_ENDPOINTS.cameras);
        const normalized = Array.isArray(data) ? data : [];
        normalized.sort((a, b) => (a.location || '').localeCompare(b.location || ''));
        setCameraFeeds(normalized);

        setSelectedCamera((previous) => {
          if (normalized.length === 0) {
            return null;
          }
          const match = previous ? normalized.find((feed) => feed.id === previous.id) : null;
          return match ?? normalized[0];
        });

        setError(null);
      } catch (err) {
        console.error('Failed to load camera feeds', err);
        setError(err instanceof Error ? err.message : 'カメラ情報の取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchCameras();
    const interval = setInterval(fetchCameras, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchTsunamiAlerts = async () => {
      try {
        const alerts = await apiClient.get<TsunamiAlert[]>(API_ENDPOINTS.tsunami.alerts);
        if (Array.isArray(alerts)) {
          alerts.sort(
            (a, b) =>
              (TSUNAMI_LEVEL_PRIORITY[b.level] ?? -1) - (TSUNAMI_LEVEL_PRIORITY[a.level] ?? -1)
          );
          setTsunamiAlerts(alerts);
        }
      } catch (err) {
        console.warn('Failed to load tsunami alerts', err);
      }
    };

    fetchTsunamiAlerts();
    const interval = setInterval(fetchTsunamiAlerts, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    if (!selectedCamera?.stream_url) {
      setVideoError('この地点のライブ映像URLが取得できませんでした');
      videoEl.removeAttribute('src');
      videoEl.load();
      return;
    }

    setVideoError(null);

    if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
      // Convert relative URLs to absolute URLs
      const streamUrl = selectedCamera.stream_url?.startsWith('/')
        ? `${API_BASE_URL}${selectedCamera.stream_url}`
        : selectedCamera.stream_url;
      videoEl.src = streamUrl;
      videoEl.play().catch(() => {
        setVideoError('自動再生を開始できませんでした。再生ボタンを押してください。');
      });
      return;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      // Convert relative URLs to absolute URLs for HLS.js
      const streamUrl = selectedCamera.stream_url?.startsWith('/')
        ? `${API_BASE_URL}${selectedCamera.stream_url}`
        : selectedCamera.stream_url;
      hls.loadSource(streamUrl);
      hls.attachMedia(videoEl);
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          setVideoError('ライブ映像の再生に失敗しました');
        }
      });
      hlsRef.current = hls;
      return () => {
        hls.destroy();
        hlsRef.current = null;
      };
    }

    setVideoError('このブラウザはHLS再生をサポートしていません');
  }, [selectedCamera?.stream_url]);

  const activeTsunamiAlert = tsunamiAlerts[0];
  const tsunamiLevel = activeTsunamiAlert?.level ?? 'information';
  const tsunamiClass = levelColorMap[tsunamiLevel] || 'text-slate-300 border-slate-500/60';

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="bg-[#1a2942] p-3 border-b border-gray-700 flex items-center justify-between flex-shrink-0">
        <div>
          <div className="text-lg font-bold text-white">沿岸ライブ監視 / TSUNAMI WATCH</div>
          <div className="text-xs text-gray-400">
            海上保安庁ライブカメラと津波監視ステータスを統合表示
          </div>
        </div>
        <div className={`px-4 py-1 rounded-full border text-sm font-semibold ${tsunamiClass}`}>
          {activeTsunamiAlert
            ? `${activeTsunamiAlert.location} - ${activeTsunamiAlert.level.toUpperCase()}`
            : '津波情報：平常'}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-0.5 bg-black/60 min-h-0 overflow-hidden">
        <div className="col-span-7 relative min-h-0 overflow-hidden">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
              海岸カメラ情報を読み込んでいます...
            </div>
          ) : error ? (
            <div className="w-full h-full flex flex-col items-center justify-center text-red-400 text-sm">
              <p>ライブカメラ情報の取得に失敗しました</p>
              <p className="text-xs text-gray-500 mt-2">{error}</p>
            </div>
          ) : (
            <MapContainer
              center={[JAPAN_CENTER.lat, JAPAN_CENTER.lng]}
              zoom={5}
              className="h-full w-full"
              zoomControl={false}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url={OSM_TILE_URL}
              />
              {camerasWithCoordinates.map((camera) => (
                <Marker
                  key={camera.id}
                  position={[camera.coordinates!.lat, camera.coordinates!.lng]}
                  icon={createLabelIcon(camera.name, camera.id === selectedCamera?.id)}
                  eventHandlers={{
                    click: () => setSelectedCamera(camera),
                  }}
                >
                  <Tooltip direction="top" offset={[0, -20]} opacity={0.9}>
                    <div className="text-xs">
                      <div className="font-semibold">{camera.name}</div>
                      <div className="text-gray-400">{camera.location}</div>
                      <div className="mt-1 text-emerald-300">クリックでライブ映像を表示</div>
                    </div>
                  </Tooltip>
                </Marker>
              ))}
            </MapContainer>
          )}

          <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-2 rounded shadow-lg text-xs space-y-1">
            <div className="font-semibold">登録地点: {cameraFeeds.length}</div>
            <div>地図表示: {camerasWithCoordinates.length}</div>
            {activeTsunamiAlert && (
              <div className="text-amber-300">
                最終更新 {new Date(activeTsunamiAlert.time).toLocaleTimeString('ja-JP')}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-5 bg-[#060c1c] flex flex-col border-l border-gray-800 min-h-0 overflow-hidden">
          <div className="p-4 border-b border-gray-800 flex-shrink-0">
            <div className="text-sm text-gray-400">選択中の地点</div>
            <div className="text-xl font-semibold text-white">{selectedCamera?.name ?? '未選択'}</div>
            <div className="text-xs text-gray-500 mt-1">{selectedCamera?.location}</div>
          </div>

          <div className="px-4 py-3 flex-shrink-0">
            <div className="relative rounded-xl overflow-hidden border border-gray-700 bg-black">
              <video
                ref={videoRef}
                controls
                playsInline
                muted
                poster={selectedCamera?.thumbnail_url ?? undefined}
                className="w-full aspect-video bg-black"
              />
              {videoError && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-sm text-red-300 bg-black/70 px-4 text-center">
                  {videoError}
                </div>
              )}
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
              <span>
                更新:{" "}
                {selectedCamera?.last_updated
                  ? new Date(selectedCamera.last_updated).toLocaleTimeString('ja-JP')
                  : '--:--:--'}
              </span>
              {selectedCamera && (
                <a
                  href={`https://camera.mics.kaiho.mlit.go.jp/camstream/${selectedCamera.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-emerald-300 hover:underline"
                >
                  公式サイトで見る ↗
                </a>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="px-4 py-2 text-xs text-gray-400 border-b border-gray-800">
              クリックして地点を切り替え
            </div>
            {cameraFeeds.map((camera) => (
              <button
                key={camera.id}
                onClick={() => setSelectedCamera(camera)}
                className={`w-full text-left px-4 py-2 border-b border-gray-900 text-sm transition-colors ${
                  camera.id === selectedCamera?.id
                    ? 'bg-emerald-500/10 text-white'
                    : 'text-gray-300 hover:bg-white/5'
                }`}
              >
                <div className="font-semibold">{camera.name}</div>
                <div className="text-xs text-gray-400 flex justify-between">
                  <span>{camera.location}</span>
                  {!camera.coordinates && <span className="text-rose-300">地図未設定</span>}
                </div>
              </button>
            ))}

            {cameraFeeds.length === 0 && !isLoading && (
              <div className="p-6 text-center text-gray-500 text-sm">
                現在表示できる沿岸カメラはありません
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoastGuardCameraPanel;

