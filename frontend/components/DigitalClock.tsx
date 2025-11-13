"use client";

import React, { useState, useEffect } from 'react';

interface DigitalClockProps {
  className?: string;
  showSeconds?: boolean;
}

const DigitalClock: React.FC<DigitalClockProps> = ({ 
  className = "", 
  showSeconds = true 
}) => {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      
      if (showSeconds) {
        setTime(`${hours}:${minutes}:${seconds}`);
      } else {
        setTime(`${hours}:${minutes}`);
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, [showSeconds]);

  return (
    <div className={`font-mono font-bold ${className}`}>
      {time || '--:--:--'}
    </div>
  );
};

export default DigitalClock;

