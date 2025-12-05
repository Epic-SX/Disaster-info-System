"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiRequest, API_ENDPOINTS } from '@/lib/api-config';
import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react';

interface JMATsunamiStatus {
  message: string;
  has_warning: boolean;
  warning_type: string | null;
  affected_areas: string[];
  timestamp: string | null;
  source: string;
}

const TsunamiAlert: React.FC = () => {
  const [jmaStatus, setJmaStatus] = useState<JMATsunamiStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJmaStatus = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiRequest<JMATsunamiStatus>(API_ENDPOINTS.tsunami.jmaStatus);
        setJmaStatus(data);
      } catch (err) {
        console.error('Error fetching JMA tsunami status:', err);
        setError('データの取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchJmaStatus();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchJmaStatus, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    if (!jmaStatus) return 'border-l-blue-500';
    if (jmaStatus.has_warning) {
      if (jmaStatus.warning_type === '大津波警報') return 'border-l-red-600';
      if (jmaStatus.warning_type === '津波警報') return 'border-l-red-500';
      if (jmaStatus.warning_type === '津波注意報') return 'border-l-yellow-500';
      return 'border-l-orange-500';
    }
    return 'border-l-green-500';
  };

  const getStatusIcon = () => {
    if (!jmaStatus) return null;
    if (jmaStatus.has_warning) {
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    }
    return <CheckCircle2 className="h-5 w-5 text-green-500" />;
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return null;
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return null;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          🌊 津波警報システム
          {jmaStatus?.source === 'JMA' && (
            <Badge variant="outline" className="text-xs">JMA</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-muted rounded w-3/4"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
            </div>
          </div>
        ) : error ? (
          <Alert className="border-l-4 border-l-red-500">
            <AlertDescription className="text-red-600">
              {error}
            </AlertDescription>
          </Alert>
        ) : jmaStatus ? (
          <div className="space-y-3">
            {/* Main Status Message - Similar to JMA website format */}
            <Alert className={`border-l-4 ${getStatusColor()} bg-muted/50`}>
              <div className="flex items-start gap-3">
                {getStatusIcon()}
                <AlertDescription className="flex-1">
                  <div className="font-medium text-base mb-1">
                    {jmaStatus.message}
                  </div>
                  {jmaStatus.has_warning && jmaStatus.affected_areas.length > 0 && (
                    <div className="text-sm text-muted-foreground mt-2">
                      <span className="font-semibold">対象地域:</span> {jmaStatus.affected_areas.join(', ')}
                    </div>
                  )}
                  {jmaStatus.timestamp && (
                    <div className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      更新: {formatTimestamp(jmaStatus.timestamp)}
                    </div>
                  )}
                </AlertDescription>
              </div>
            </Alert>

            {/* Warning Badge if active */}
            {jmaStatus.has_warning && jmaStatus.warning_type && (
              <div className="flex items-center gap-2">
                <Badge 
                  variant={jmaStatus.warning_type === '大津波警報' ? 'destructive' : 'default'}
                  className={
                    jmaStatus.warning_type === '大津波警報' 
                      ? 'bg-red-600 text-white' 
                      : jmaStatus.warning_type === '津波警報'
                      ? 'bg-red-500 text-white'
                      : 'bg-yellow-500 text-white'
                  }
                >
                  {jmaStatus.warning_type}
                </Badge>
              </div>
            )}
          </div>
        ) : (
          <Alert className="border-l-4 border-l-gray-400">
            <AlertDescription>
              データが利用できません
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default TsunamiAlert; 