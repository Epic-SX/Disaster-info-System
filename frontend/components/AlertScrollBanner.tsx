"use client";

import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

interface AlertScrollBannerProps {
  alerts?: string[];
  backgroundColor?: string;
  textColor?: string;
}

const AlertScrollBanner: React.FC<AlertScrollBannerProps> = ({ 
  alerts: propAlerts,
  backgroundColor = '#1e40af',
  textColor = '#ffffff'
}) => {
  const [alerts, setAlerts] = useState<string[]>(
    propAlerts || [
      '【要監視中】岩手・三陸沖群発地震>避難グッズ見直して!!',
      '【重要】防災グッズの有効期限をチェックしてください',
      '【注意】最近の地震活動が活発化しています - 備えを確認してください'
    ]
  );
  const [scrollPosition, setScrollPosition] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scrollInterval = setInterval(() => {
      setScrollPosition(prev => {
        const newPosition = prev + 1;
        const maxScroll = container.scrollWidth / 2;
        return newPosition >= maxScroll ? 0 : newPosition;
      });
    }, 30); // Adjust speed here

    return () => clearInterval(scrollInterval);
  }, [alerts]);

  const alertText = alerts.join(' • ');
  const duplicatedText = `${alertText} • ${alertText}`;

  return (
    <div 
      className="relative overflow-hidden py-3 px-4"
      style={{ backgroundColor }}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className="flex-shrink-0">
          <div className="bg-red-600 rounded-full p-2">
            <AlertTriangle className="h-5 w-5 text-white" />
          </div>
        </div>

        {/* Label */}
        <div 
          className="font-bold text-lg flex-shrink-0"
          style={{ color: textColor }}
        >
          地震情報
        </div>

        {/* Scrolling Text */}
        <div 
          ref={containerRef}
          className="flex-1 overflow-hidden whitespace-nowrap"
        >
          <div
            className="inline-block font-bold"
            style={{ 
              color: '#ff4444',
              transform: `translateX(-${scrollPosition}px)`,
              transition: 'transform 0.03s linear'
            }}
          >
            {duplicatedText}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertScrollBanner;

