import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const NewsAggregator: React.FC = () => {
  const newsItems = [
    {
      id: 1,
      title: "緊急時対応ガイドラインが更新されました",
      source: "防災管理庁",
      time: "2時間前",
      category: "official"
    },
    {
      id: 2,
      title: "気象警報：大雨が予想されています",
      source: "気象庁",
      time: "4時間前",
      category: "weather"
    },
    {
      id: 3,
      title: "地域緊急対応訓練のお知らせ",
      source: "地方自治体",
      time: "1日前",
      category: "training"
    }
  ];

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'official': return '公式';
      case 'weather': return '気象';
      case 'training': return '訓練';
      default: return category;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold">📰 ニュース・お知らせ</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {newsItems.map((item) => (
            <div key={item.id} className="border-b pb-3 last:border-b-0">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-sm">{item.title}</h3>
                <Badge variant="outline" className="ml-2">
                  {getCategoryLabel(item.category)}
                </Badge>
              </div>
              <div className="text-xs text-gray-600">
                {item.source} • {item.time}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default NewsAggregator; 