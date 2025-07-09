'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Waves, Clock, AlertTriangle } from 'lucide-react';
import { TsunamiInfo, P2PApiResponse } from '@/app/types/disaster';

export default function TsunamiInfoComponent() {
  const [tsunamiData, setTsunamiData] = useState<TsunamiInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTsunamiData = async () => {
      try {
        // P2P地震情報APIから津波情報を取得
        const response = await fetch('https://api.p2pquake.net/v2/history?codes=552&limit=5');
        const data: P2PApiResponse[] = await response.json();
        
        const formattedData: TsunamiInfo[] = data.map((item: P2PApiResponse) => ({
          id: item.id,
          time: item.time,
          grade: item.tsunami?.grade || '',
          immediate: item.tsunami?.immediate || false,
          areas: item.tsunami?.areas || [],
        }));

        setTsunamiData(formattedData);
      } catch (error) {
        console.error('津波情報の取得に失敗しました:', error);
        // フォールバック用のダミーデータ
        setTsunamiData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTsunamiData();
    const interval = setInterval(fetchTsunamiData, 60000); // 1分ごとに更新

    return () => clearInterval(interval);
  }, []);

  const getTsunamiGradeColor = (grade: string) => {
    switch (grade) {
      case '大津波警報': return 'bg-red-600';
      case '津波警報': return 'bg-orange-500';
      case '津波注意報': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  if (loading) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Waves className="h-5 w-5 text-blue-500" />
            津波情報
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">読み込み中...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Waves className="h-5 w-5 text-blue-500" />
          津波情報
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 max-h-96 overflow-y-auto">
        {tsunamiData.length === 0 ? (
          <div className="text-center py-8 text-green-600">
            <div className="text-lg font-semibold">津波の心配なし</div>
            <div className="text-sm text-gray-600 mt-2">
              現在、津波警報・注意報は発表されていません
            </div>
          </div>
        ) : (
          tsunamiData.map((tsunami) => (
            <div key={tsunami.id} className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <Badge className={`${getTsunamiGradeColor(tsunami.grade)} text-white`}>
                  {tsunami.grade}
                </Badge>
                {tsunami.immediate && (
                  <Badge variant="destructive" className="animate-pulse">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    即座に避難
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Clock className="h-4 w-4" />
                {new Date(tsunami.time).toLocaleString('ja-JP')}
              </div>
              
              {tsunami.areas && tsunami.areas.length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">対象地域:</div>
                  <div className="space-y-1">
                    {tsunami.areas.map((area, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <span>{area.name}</span>
                        <Badge 
                          variant="outline" 
                          className={area.immediate ? 'border-red-500 text-red-500' : ''}
                        >
                          {area.grade}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        
        {/* 津波情報の注意事項 */}
        <div className="mt-6 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-sm text-blue-800">
            <div className="font-medium mb-1">津波情報について</div>
            <ul className="text-xs space-y-1">
              <li>• 津波は繰り返し襲来します</li>
              <li>• 警報解除まで海岸に近づかないでください</li>
              <li>• 高台や頑丈な建物の上階に避難してください</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 