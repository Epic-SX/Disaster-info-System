"use client";

import React, { useEffect, useRef, useState } from 'react';
import { apiClient, API_ENDPOINTS } from '@/lib/api-config';

interface SeismicStation {
  id: string;
  name: string;
  location: string;
  data: number[]; // Waveform data points
  maxAmplitude: number;
  latitude?: number;
  longitude?: number;
  earthquakeInfluence?: number;
}

interface BackendWaveformData {
  stations: Array<{
    id: string;
    name: string;
    location: string;
    latitude: number;
    longitude: number;
    waveform: number[];
    current_amplitude: number;
    max_amplitude: number;
    earthquake_influence: number;
  }>;
  timestamp: string;
  recent_earthquakes_count: number;
}

interface SeismicWaveformDisplayProps {
  stations?: SeismicStation[];
  enableAnimation?: boolean; // Set to false to show all waveforms immediately
}

const SeismicWaveformDisplay: React.FC<SeismicWaveformDisplayProps> = ({ 
  stations: propStations,
  enableAnimation = true // Default to animation enabled
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stations, setStations] = useState<SeismicStation[]>(propStations || []);
  const animationRef = useRef<number | null>(null);
  const [isBackendAvailable, setIsBackendAvailable] = useState<boolean>(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [earthquakeCount, setEarthquakeCount] = useState<number>(0);
  
  // Track visible points for sequential drawing animation
  const [visiblePointCount, setVisiblePointCount] = useState<number>(0);
  const [maxDataLength, setMaxDataLength] = useState<number>(0);
  const drawSpeedRef = useRef<number>(5); // Points to add per frame (adjust for speed)

  // Fetch waveform data from backend
  useEffect(() => {
    const fetchWaveformData = async () => {
      try {
        const data = await apiClient.get<BackendWaveformData>(API_ENDPOINTS.seismic.waveform);
        
        if (data && data.stations) {
          // Convert backend data to frontend format
          const convertedStations: SeismicStation[] = data.stations.map(station => ({
            id: station.id,
            name: station.name,
            location: station.location,
            data: station.waveform,
            maxAmplitude: station.max_amplitude,
            latitude: station.latitude,
            longitude: station.longitude,
            earthquakeInfluence: station.earthquake_influence,
          }));
          
          setStations(convertedStations);
          setLastUpdate(data.timestamp);
          setEarthquakeCount(data.recent_earthquakes_count);
          setIsBackendAvailable(true);
          
          // Calculate max data length and reset animation
          const newMaxLength = Math.max(...convertedStations.map(s => s.data.length));
          console.log('Waveform data received:', {
            stationCount: convertedStations.length,
            maxDataLength: newMaxLength,
            sampleData: convertedStations[0]?.data.slice(0, 5)
          });
          
          if (newMaxLength !== maxDataLength) {
            setMaxDataLength(newMaxLength);
            // If animation is disabled, show all points immediately
            setVisiblePointCount(enableAnimation ? 0 : newMaxLength);
          }
        }
      } catch (error) {
        console.error('Error fetching waveform data:', error);
        setIsBackendAvailable(false);
        
        // Fallback to default stations on error
        if (stations.length === 0) {
          const defaultStations: SeismicStation[] = [
            { id: '1', name: '北海道', location: '釧路支庁釧路', data: [], maxAmplitude: 0 },
            { id: '2', name: '北海道', location: '胆振支庁苫小牧', data: [], maxAmplitude: 0 },
            { id: '3', name: '新潟県', location: '新潟', data: [], maxAmplitude: 0 },
            { id: '4', name: '石川県', location: '正院', data: [], maxAmplitude: 0 },
            { id: '5', name: '埼玉県', location: '岩槻', data: [], maxAmplitude: 0 },
            { id: '6', name: '東京都', location: '新宿', data: [], maxAmplitude: 0 },
            { id: '7', name: '神奈川県', location: '相模原', data: [], maxAmplitude: 0 },
            { id: '8', name: '大阪府', location: '堺', data: [], maxAmplitude: 0 },
            { id: '9', name: '宮崎県', location: '都城', data: [], maxAmplitude: 0 },
            { id: '10', name: '沖縄県', location: '名護', data: [], maxAmplitude: 0 },
          ];
          setStations(defaultStations);
        }
      }
    };

    // Initial fetch
    fetchWaveformData();

    // Update every 1 second to get new waveform data from backend
    const interval = setInterval(fetchWaveformData, 1000);
    return () => clearInterval(interval);
  }, [enableAnimation, maxDataLength, stations.length]);

  // Handle prop changes
  useEffect(() => {
    if (propStations && propStations.length > 0) {
      setStations(propStations);
    }
  }, [propStations]);

  // Animate the sequential drawing of waveforms
  useEffect(() => {
    // Skip animation if disabled
    if (!enableAnimation) {
      return;
    }
    
    // Don't animate if no data or animation is complete
    if (maxDataLength === 0 || visiblePointCount >= maxDataLength) {
      if (maxDataLength > 0 && visiblePointCount >= maxDataLength) {
        console.log('Animation complete:', visiblePointCount, '/', maxDataLength);
      }
      return;
    }

    console.log('Starting animation:', visiblePointCount, '/', maxDataLength);
    
    const animationInterval = setInterval(() => {
      setVisiblePointCount((prev) => {
        const next = prev + drawSpeedRef.current;
        return next >= maxDataLength ? maxDataLength : next;
      });
    }, 16); // ~60fps

    return () => clearInterval(animationInterval);
  }, [visiblePointCount, maxDataLength, enableAnimation]);

  // Draw waveforms on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      // Set canvas size
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      // Clear canvas
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, rect.width, rect.height);

      const rowHeight = rect.height / stations.length;
      const waveformScale = rowHeight / 3; // Adjust amplitude scaling

      stations.forEach((station, index) => {
        const y = index * rowHeight + rowHeight / 2;
        const dataPoints = station.data;

        // Draw horizontal grid line (baseline)
        ctx.strokeStyle = '#1a3a52';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(rect.width, y);
        ctx.stroke();

        // Draw station label
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${station.name} ${station.location}`, 5, y);

        // Draw waveform with sequential animation (fills full width)
        if (dataPoints.length > 1) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1;
          ctx.beginPath();

          // Only draw up to visiblePointCount for sequential animation
          const pointsToDraw = Math.min(visiblePointCount, dataPoints.length);
          
          if (pointsToDraw > 0) {
            // Calculate pixel spacing to fill the width based on total data length
            // This ensures the waveform will eventually fill the entire width
            const availableWidth = rect.width;
            const pixelSpacing = availableWidth / dataPoints.length;
            
            let firstPoint = true;
            
            for (let pointIndex = 0; pointIndex < pointsToDraw; pointIndex++) {
              const value = dataPoints[pointIndex];
              const x = pointIndex * pixelSpacing;
              const waveY = y - (value * waveformScale);
              
              if (firstPoint) {
                ctx.moveTo(x, waveY);
                firstPoint = false;
              } else {
                ctx.lineTo(x, waveY);
              }
            }

            ctx.stroke();
          }
        }
      });

      // Draw scale indicator
      ctx.fillStyle = '#ffffff';
      ctx.font = '10px monospace';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'bottom';
      ctx.fillText('2gal/row', rect.width - 5, rect.height - 5);

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [stations, visiblePointCount]);

  return (
    <div className="relative w-full h-full bg-black">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ imageRendering: 'crisp-edges' }}
      />
      
      {/* Status Indicator */}
      <div className="absolute top-2 right-2 flex flex-col gap-1 text-xs font-mono">
        <div className={`px-2 py-1 rounded ${isBackendAvailable ? 'bg-green-900/80 text-green-200' : 'bg-red-900/80 text-red-200'}`}>
          {isBackendAvailable ? '● LIVE' : '● OFFLINE'}
        </div>
        {isBackendAvailable && earthquakeCount > 0 && (
          <div className="px-2 py-1 rounded bg-yellow-900/80 text-yellow-200">
            {earthquakeCount} EQ Active
          </div>
        )}
        {lastUpdate && (
          <div className="px-2 py-1 rounded bg-gray-900/80 text-gray-400 text-[10px]">
            {new Date(lastUpdate).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default SeismicWaveformDisplay;

