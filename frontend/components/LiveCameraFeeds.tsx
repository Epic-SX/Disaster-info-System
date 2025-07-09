import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const LiveCameraFeeds: React.FC = () => {
  const cameraFeeds = [
    {
      id: 1,
      name: "東京湾",
      status: "online",
      location: "東京都心部"
    },
    {
      id: 2,
      name: "富士山",
      status: "online",
      location: "静岡県"
    },
    {
      id: 3,
      name: "大阪港",
      status: "maintenance",
      location: "大阪府"
    }
  ];

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'online': return 'オンライン';
      case 'maintenance': return 'メンテナンス中';
      default: return status;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold">📹 ライブカメラ映像</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {cameraFeeds.map((feed) => (
            <div key={feed.id} className="border rounded-lg p-3">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold">{feed.name}</h3>
                <Badge variant={feed.status === 'online' ? 'default' : 'secondary'}>
                  {getStatusLabel(feed.status)}
                </Badge>
              </div>
              <div className="bg-gray-200 h-32 rounded flex items-center justify-center mb-2">
                {feed.status === 'online' ? '📹 ライブ映像' : '🔧 メンテナンス中'}
              </div>
              <div className="text-sm text-gray-600">{feed.location}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default LiveCameraFeeds; 