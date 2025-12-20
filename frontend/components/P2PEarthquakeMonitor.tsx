"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';
import { 
  AlertTriangle, 
  Activity, 
  MapPin, 
  Clock, 
  Zap,
  Waves,
  Radio,
  RefreshCw,
  TrendingUp,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

// Types based on P2P API specification
interface P2PEarthquake {
  id: string;
  time: string;
  location: string;
  magnitude: number | null;
  depth: number | null;
  latitude: number | null;
  longitude: number | null;
  maxScale: number | null;
  maxScaleString: string;
  tsunami: boolean;
  source: string;
  issueType: string;
}

interface P2PTsunami {
  id: string;
  time: string;
  cancelled: boolean;
  areas: Array<{
    name: string;
    grade: string;
    immediate: boolean;
    maxHeight: string | null;
  }>;
  source: string;
}

interface P2PEEW {
  id: string;
  time: string;
  eventId: string;
  serial: string;
  cancelled: boolean;
  test: boolean;
  earthquake: {
    location: string | null;
    magnitude: number | null;
    latitude: number | null;
    longitude: number | null;
    depth: number | null;
    originTime: string | null;
    arrivalTime: string | null;
  } | null;
  areas: Array<{
    pref: string;
    name: string;
    scaleFrom: number;
    scaleTo: number;
    kindCode: string | null;
    arrivalTime: string | null;
  }>;
  source: string;
}

interface P2PServiceStatus {
  service_available: boolean;
  websocket_monitoring: boolean;
  websocket_connected: boolean;
  environment: string;
  data_status: {
    latest_data_types: number;
    history_items: number;
    registered_callbacks: number;
  };
  information_codes: Record<string, string>;
  last_updated: string;
}

const P2PEarthquakeMonitor: React.FC = () => {
  const [earthquakes, setEarthquakes] = useState<P2PEarthquake[]>([]);
  const [tsunamis, setTsunamis] = useState<P2PTsunami[]>([]);
  const [eewAlerts, setEEWAlerts] = useState<P2PEEW[]>([]);
  const [serviceStatus, setServiceStatus] = useState<P2PServiceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadAllData = async () => {
    try {
      setError('');
      
      // Load all data in parallel
      const [earthquakesRes, tsunamisRes, eewRes, statusRes] = await Promise.allSettled([
        apiClient.get<{earthquakes: P2PEarthquake[]}>(API_ENDPOINTS.p2p.latestEarthquakes),
        apiClient.get<{tsunamis: P2PTsunami[]}>(API_ENDPOINTS.p2p.latestTsunamis),
        apiClient.get<{eew: P2PEEW[]}>(API_ENDPOINTS.p2p.latestEEW),
        apiClient.get<P2PServiceStatus>(API_ENDPOINTS.p2p.status)
      ]);

      if (earthquakesRes.status === 'fulfilled' && earthquakesRes.value.earthquakes) {
        setEarthquakes(earthquakesRes.value.earthquakes);
      }

      if (tsunamisRes.status === 'fulfilled' && tsunamisRes.value.tsunamis) {
        // Deduplicate tsunamis by creating a unique key from id, time, and source
        const seen = new Set<string>();
        const uniqueTsunamis = tsunamisRes.value.tsunamis.filter((tsunami: P2PTsunami) => {
          const uniqueKey = `${tsunami.id}-${tsunami.time}-${tsunami.source}`;
          if (seen.has(uniqueKey)) {
            return false;
          }
          seen.add(uniqueKey);
          return true;
        });
        setTsunamis(uniqueTsunamis);
      }

      if (eewRes.status === 'fulfilled' && eewRes.value.eew) {
        setEEWAlerts(eewRes.value.eew);
      }

      if (statusRes.status === 'fulfilled') {
        setServiceStatus(statusRes.value);
      }

      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error loading P2P data:', err);
      setError('P2P地震情報の読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const getMagnitudeColor = (magnitude: number | null) => {
    if (!magnitude) return 'bg-gray-500';
    if (magnitude >= 7.0) return 'bg-red-600';
    if (magnitude >= 6.0) return 'bg-red-500';
    if (magnitude >= 5.0) return 'bg-orange-500';
    if (magnitude >= 4.0) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getScaleColor = (scale: number | null) => {
    if (!scale || scale < 0) return 'bg-gray-500';
    if (scale >= 60) return 'bg-red-600'; // 震度6強以上
    if (scale >= 55) return 'bg-red-500'; // 震度6弱
    if (scale >= 50) return 'bg-orange-500'; // 震度5強
    if (scale >= 45) return 'bg-yellow-500'; // 震度5弱
    if (scale >= 40) return 'bg-blue-500'; // 震度4
    return 'bg-green-500'; // 震度3以下
  };

  const getTsunamiGradeColor = (grade: string) => {
    switch (grade) {
      case 'MajorWarning': return 'bg-red-600 text-white';
      case 'Warning': return 'bg-red-500 text-white';
      case 'Watch': return 'bg-yellow-500 text-black';
      default: return 'bg-gray-500 text-white';
    }
  };

  const formatDateTime = (timeStr: string) => {
    try {
      // P2P API format: "2006/01/02 15:04:05.999"
      const date = new Date(timeStr.replace(/\//g, '-'));
      return date.toLocaleString('ja-JP');
    } catch {
      return timeStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Service Status Header */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Radio className="h-5 w-5" />
              P2P地震情報 リアルタイム監視
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={loadAllData}
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              {serviceStatus?.service_available ? (
                <Badge variant="outline" className="text-green-600 border-green-600">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  接続中
                </Badge>
              ) : (
                <Badge variant="outline" className="text-red-600 border-red-600">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  未接続
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>最終更新: {lastUpdate.toLocaleTimeString('ja-JP')}</span>
            {serviceStatus && (
              <>
                <span>環境: {serviceStatus.environment}</span>
                <span>WebSocket: {serviceStatus.websocket_connected ? '接続中' : '切断中'}</span>
              </>
            )}
          </div>
        </CardHeader>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="earthquakes" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="earthquakes" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            地震情報
            {earthquakes.length > 0 && (
              <Badge variant="secondary">{earthquakes.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="tsunamis" className="flex items-center gap-2">
            <Waves className="h-4 w-4" />
            津波予報
            {tsunamis.length > 0 && (
              <Badge variant="secondary">{tsunamis.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="eew" className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            緊急地震速報
            {eewAlerts.length > 0 && (
              <Badge variant="secondary">{eewAlerts.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="earthquakes">
          <Card>
            <CardHeader>
              <CardTitle>最新の地震情報</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {earthquakes.length > 0 ? (
                    earthquakes.map((quake) => (
                      <div
                        key={quake.id}
                        className="p-4 border rounded-lg space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">{quake.location}</span>
                            {quake.tsunami && (
                              <Badge variant="destructive">津波</Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {quake.magnitude && (
                              <Badge className={getMagnitudeColor(quake.magnitude)}>
                                M{quake.magnitude}
                              </Badge>
                            )}
                            <Badge className={getScaleColor(quake.maxScale)}>
                              震度{quake.maxScaleString}
                            </Badge>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDateTime(quake.time)}
                          </span>
                          {quake.depth && (
                            <span>深さ: {quake.depth}km</span>
                          )}
                          <span>発表種別: {quake.issueType}</span>
                        </div>
                        {quake.latitude && quake.longitude && (
                          <div className="text-xs text-muted-foreground">
                            座標: {quake.latitude.toFixed(1)}°N, {quake.longitude.toFixed(1)}°E
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      現在、地震情報はありません
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tsunamis">
          <Card>
            <CardHeader>
              <CardTitle>津波予報</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {tsunamis.length > 0 ? (
                    tsunamis.map((tsunami, index) => (
                      <div
                        key={`tsunami-${tsunami.id}-${tsunami.time}-${index}`}
                        className={`p-4 border rounded-lg space-y-2 ${
                          tsunami.cancelled ? 'bg-gray-50' : 'bg-blue-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium">
                            {tsunami.cancelled ? '津波予報解除' : '津波予報発表'}
                          </span>
                          <Badge variant={tsunami.cancelled ? 'secondary' : 'destructive'}>
                            {tsunami.cancelled ? '解除' : '発表中'}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <Clock className="h-3 w-3 inline mr-1" />
                          {formatDateTime(tsunami.time)}
                        </div>
                        {tsunami.areas.length > 0 && (
                          <div className="space-y-1">
                            <div className="text-sm font-medium">対象地域:</div>
                            {tsunami.areas.map((area, index) => (
                              <div key={index} className="flex items-center justify-between text-sm">
                                <span>{area.name}</span>
                                <div className="flex items-center gap-2">
                                  <Badge className={getTsunamiGradeColor(area.grade)}>
                                    {area.grade === 'MajorWarning' && '大津波警報'}
                                    {area.grade === 'Warning' && '津波警報'}
                                    {area.grade === 'Watch' && '津波注意報'}
                                    {area.grade === 'Unknown' && '不明'}
                                  </Badge>
                                  {area.immediate && (
                                    <Badge variant="destructive">直ちに来襲</Badge>
                                  )}
                                  {area.maxHeight && (
                                    <span className="text-xs">{area.maxHeight}</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      現在、津波予報はありません
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="eew">
          <Card>
            <CardHeader>
              <CardTitle>緊急地震速報</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {eewAlerts.length > 0 ? (
                    eewAlerts.map((eew) => (
                      <div
                        key={eew.id}
                        className={`p-4 border rounded-lg space-y-2 ${
                          eew.cancelled ? 'bg-gray-50' : 
                          eew.test ? 'bg-yellow-50' : 'bg-red-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            <span className="font-medium">緊急地震速報</span>
                            <span className="text-sm text-muted-foreground">
                              #{eew.serial}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {eew.test && <Badge variant="outline">テスト</Badge>}
                            {eew.cancelled && <Badge variant="secondary">取消</Badge>}
                            {!eew.cancelled && !eew.test && (
                              <Badge variant="destructive">警報</Badge>
                            )}
                          </div>
                        </div>
                        
                        {eew.earthquake && (
                          <div className="space-y-1">
                            <div className="flex items-center justify-between">
                              <span>震源: {eew.earthquake.location || '不明'}</span>
                              {eew.earthquake.magnitude && (
                                <Badge className={getMagnitudeColor(eew.earthquake.magnitude)}>
                                  M{eew.earthquake.magnitude}
                                </Badge>
                              )}
                            </div>
                            {eew.earthquake.originTime && (
                              <div className="text-sm text-muted-foreground">
                                発生時刻: {formatDateTime(eew.earthquake.originTime)}
                              </div>
                            )}
                            {eew.earthquake.depth && (
                              <div className="text-sm text-muted-foreground">
                                深さ: {eew.earthquake.depth}km
                              </div>
                            )}
                          </div>
                        )}

                        <div className="text-sm text-muted-foreground">
                          <Clock className="h-3 w-3 inline mr-1" />
                          発表: {formatDateTime(eew.time)}
                        </div>

                        {eew.areas.length > 0 && (
                          <div className="space-y-1">
                            <div className="text-sm font-medium">予想震度:</div>
                            <div className="grid grid-cols-1 gap-1 text-sm">
                              {eew.areas.slice(0, 3).map((area, index) => (
                                <div key={index} className="flex items-center justify-between">
                                  <span>{area.name}</span>
                                  <span>震度{area.scaleFrom/10}～{area.scaleTo === 99 ? '以上' : area.scaleTo/10}</span>
                                </div>
                              ))}
                              {eew.areas.length > 3 && (
                                <div className="text-muted-foreground text-xs">
                                  ...他{eew.areas.length - 3}地域
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      現在、緊急地震速報はありません
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Service Information */}
      {serviceStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">サービス情報</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground">データ種別</div>
                <div className="font-medium">{serviceStatus.data_status.latest_data_types}種類</div>
              </div>
              <div>
                <div className="text-muted-foreground">履歴件数</div>
                <div className="font-medium">{serviceStatus.data_status.history_items}件</div>
              </div>
              <div>
                <div className="text-muted-foreground">コールバック</div>
                <div className="font-medium">{serviceStatus.data_status.registered_callbacks}個</div>
              </div>
              <div>
                <div className="text-muted-foreground">環境</div>
                <div className="font-medium">
                  {serviceStatus.environment === 'sandbox' ? 'サンドボックス' : '本番環境'}
                </div>
              </div>
            </div>
            <div className="mt-4 text-xs text-muted-foreground">
              P2P地震情報 JSON API (v2) による情報提供
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default P2PEarthquakeMonitor; 