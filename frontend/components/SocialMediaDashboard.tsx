import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const SocialMediaDashboard: React.FC = () => {
  const socialData = [
    {
      platform: "Twitter",
      posts: 15,
      engagement: "85%",
      lastPost: "2時間前",
      status: "active"
    },
    {
      platform: "Facebook",
      posts: 8,
      engagement: "92%",
      lastPost: "4時間前",
      status: "active"
    },
    {
      platform: "Instagram",
      posts: 5,
      engagement: "78%",
      lastPost: "6時間前",
      status: "scheduled"
    }
  ];

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active': return 'アクティブ';
      case 'scheduled': return '投稿予約済み';
      default: return status;
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">📱 ソーシャルメディア管理</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {socialData.map((platform) => (
              <div key={platform.platform} className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-semibold">{platform.platform}</h3>
                  <Badge variant={platform.status === 'active' ? 'default' : 'secondary'}>
                    {getStatusLabel(platform.status)}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <div>本日の投稿数: {platform.posts}</div>
                  <div>エンゲージメント率: {platform.engagement}</div>
                  <div>最新投稿: {platform.lastPost}</div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-6 space-y-4">
            <h4 className="font-semibold">クイックアクション</h4>
            <div className="flex gap-2 flex-wrap">
              <Button size="sm">緊急投稿</Button>
              <Button size="sm" variant="outline">投稿予約</Button>
              <Button size="sm" variant="outline">アナリティクス表示</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SocialMediaDashboard; 