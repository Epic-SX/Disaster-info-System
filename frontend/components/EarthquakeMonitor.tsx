'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

const EarthquakeMonitor: React.FC = () => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [fiveMinutesAgo, setFiveMinutesAgo] = useState<string>('');

  useEffect(() => {
    // Set initial times on client side only
    const now = new Date();
    const pastTime = new Date(Date.now() - 300000);
    
    setCurrentTime(now.toLocaleTimeString('ja-JP'));
    setFiveMinutesAgo(pastTime.toLocaleTimeString('ja-JP'));

    // Update time every second
    const interval = setInterval(() => {
      const newTime = new Date();
      setCurrentTime(newTime.toLocaleTimeString('ja-JP'));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const mockData = [
    {
      id: 1,
      magnitude: 4.2,
      location: "東京都心部",
      depth: "10km",
      time: currentTime || '--:--:--',
      status: "moderate"
    },
    {
      id: 2,
      magnitude: 3.8,
      location: "大阪府",
      depth: "15km", 
      time: fiveMinutesAgo || '--:--:--',
      status: "minor"
    }
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">🌊 地震監視システム</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockData.map((earthquake) => (
              <Alert key={earthquake.id} className="border-l-4 border-l-orange-500">
                <AlertDescription className="flex justify-between items-center">
                  <div>
                    <div className="font-semibold">マグニチュード{earthquake.magnitude} - {earthquake.location}</div>
                    <div className="text-sm text-gray-600">深度: {earthquake.depth} | 発生時刻: {earthquake.time}</div>
                  </div>
                  <Badge variant={earthquake.status === 'moderate' ? 'destructive' : 'secondary'}>
                    {earthquake.status === 'moderate' ? '注意' : '軽微'}
                  </Badge>
                </AlertDescription>
              </Alert>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EarthquakeMonitor; 