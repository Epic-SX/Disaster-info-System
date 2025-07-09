import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

const TsunamiAlert: React.FC = () => {
  const alerts = [
    {
      id: 1,
      level: "注意報",
      region: "太平洋沿岸",
      estimatedArrival: "現在、津波の脅威はありません",
      status: "monitoring"
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold">🌊 津波警報システム</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <Alert key={alert.id} className="border-l-4 border-l-blue-500">
              <AlertDescription className="flex justify-between items-center">
                <div>
                  <div className="font-semibold">{alert.level} - {alert.region}</div>
                  <div className="text-sm text-gray-600">{alert.estimatedArrival}</div>
                </div>
                <Badge variant="secondary">
                  {alert.status === 'monitoring' ? '監視中' : alert.status}
                </Badge>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default TsunamiAlert; 