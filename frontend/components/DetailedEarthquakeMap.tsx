"use client";

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Circle, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L, { DivIcon } from 'leaflet';

// Fix for default markers in react-leaflet
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: '/leaflet/marker-icon-2x.png',
    iconUrl: '/leaflet/marker-icon.png',
    shadowUrl: '/leaflet/marker-shadow.png',
  });
}

interface EarthquakeData {
  id: string;
  time: string;
  location: string;
  magnitude: number;
  depth: number;
  latitude: number;
  longitude: number;
  intensity: string;
  tsunami: boolean;
}

interface DetailedEarthquakeMapProps {
  earthquake?: EarthquakeData;
}

// Create custom red X marker for epicenter
const createEpicenterIcon = (): DivIcon => {
  return L.divIcon({
    className: 'custom-epicenter-icon',
    html: `
      <div style="position: relative; width: 40px; height: 40px;">
        <svg width="40" height="40" viewBox="0 0 40 40" style="position: absolute; top: -20px; left: -20px;">
          <!-- Red X marker -->
          <line x1="10" y1="10" x2="30" y2="30" stroke="#ff0000" stroke-width="4" stroke-linecap="round"/>
          <line x1="30" y1="10" x2="10" y2="30" stroke="#ff0000" stroke-width="4" stroke-linecap="round"/>
          <!-- White outline for visibility -->
          <line x1="10" y1="10" x2="30" y2="30" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.5"/>
          <line x1="30" y1="10" x2="10" y2="30" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.5"/>
        </svg>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
};

// Create custom seismic intensity marker (blue square with number)
const createIntensityIcon = (intensity: string): DivIcon => {
  // Parse intensity to get numeric value
  const intensityValue = intensity.replace(/[^0-9.]/g, '');
  const displayValue = intensityValue || intensity;
  
  // Color based on intensity
  let bgColor = '#0066cc'; // Default blue
  const textColor = '#ffffff';
  
  const numIntensity = parseFloat(intensityValue);
  if (numIntensity >= 6) {
    bgColor = '#cc0000'; // Dark red for high intensity
  } else if (numIntensity >= 5) {
    bgColor = '#ff6600'; // Orange
  } else if (numIntensity >= 4) {
    bgColor = '#ff9900'; // Light orange
  } else if (numIntensity >= 3) {
    bgColor = '#3399ff'; // Light blue
  }
  
  return L.divIcon({
    className: 'custom-intensity-icon',
    html: `
      <div style="
        background-color: ${bgColor};
        color: ${textColor};
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 16px;
        border: 2px solid white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        font-family: sans-serif;
      ">
        ${displayValue}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Component to auto-center map on earthquake location
const MapController: React.FC<{ earthquake?: EarthquakeData }> = ({ earthquake }) => {
  const map = useMap();
  
  useEffect(() => {
    if (earthquake) {
      map.setView([earthquake.latitude, earthquake.longitude], 8);
    }
  }, [earthquake, map]);
  
  return null;
};

const DetailedEarthquakeMap: React.FC<DetailedEarthquakeMapProps> = ({ earthquake }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="h-full w-full bg-[#0a1929] flex items-center justify-center">
        <div className="text-gray-500">Loading map...</div>
      </div>
    );
  }

  // Default to center of Japan if no earthquake selected
  const defaultCenter: [number, number] = [36.5, 138.0];
  const center: [number, number] = earthquake 
    ? [earthquake.latitude, earthquake.longitude]
    : defaultCenter;

  return (
    <div className="relative h-full w-full">
      {earthquake ? (
        <MapContainer
          center={center}
          zoom={8}
          className="h-full w-full"
          style={{ height: '100%', width: '100%', backgroundColor: '#1a1a2e' }}
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {/* Auto-center on earthquake */}
          <MapController earthquake={earthquake} />
          
          {/* Earthquake impact radius circle */}
          <Circle
            center={[earthquake.latitude, earthquake.longitude]}
            radius={earthquake.magnitude * 15000} // Radius in meters based on magnitude
            pathOptions={{
              color: '#ff6666',
              fillColor: '#ff0000',
              fillOpacity: 0.1,
              weight: 2,
              opacity: 0.5
            }}
          />
          
          {/* Red X marker for epicenter */}
          <Marker
            position={[earthquake.latitude, earthquake.longitude]}
            icon={createEpicenterIcon()}
          >
            <Popup>
              <div className="p-2 min-w-[200px]">
                <div className="font-bold text-sm mb-2">震源地</div>
                <div className="text-xs space-y-1">
                  <div><strong>場所:</strong> {earthquake.location}</div>
                  <div><strong>発生時刻:</strong> {new Date(earthquake.time).toLocaleString('ja-JP')}</div>
                  <div><strong>マグニチュード:</strong> M{earthquake.magnitude}</div>
                  <div><strong>深さ:</strong> {earthquake.depth}km</div>
                </div>
              </div>
            </Popup>
          </Marker>
          
          {/* Seismic intensity marker (offset slightly from epicenter) */}
          <Marker
            position={[
              earthquake.latitude + 0.15, 
              earthquake.longitude + 0.15
            ]}
            icon={createIntensityIcon(earthquake.intensity)}
          >
            <Popup>
              <div className="p-2">
                <div className="font-bold text-sm">最大震度</div>
                <div className="text-lg font-bold text-center mt-1">
                  {earthquake.intensity}
                </div>
              </div>
            </Popup>
          </Marker>
        </MapContainer>
      ) : (
        <div className="h-full w-full bg-[#0a1929] flex items-center justify-center">
          <div className="text-center text-gray-400">
            <div className="text-4xl mb-2">🗾</div>
            <div className="text-sm">地震を選択してください</div>
            <div className="text-xs mt-1">Select an earthquake to view details</div>
          </div>
        </div>
      )}
      
      {/* Info overlay */}
      {earthquake && (
        <div className="absolute top-2 left-2 z-[1000] bg-black/80 text-white px-3 py-2 rounded shadow-lg text-xs">
          <div className="font-bold">{earthquake.location}</div>
          <div>M{earthquake.magnitude} / 深さ{earthquake.depth}km</div>
          <div className="flex items-center gap-2 mt-1">
            <div className="w-6 h-6 bg-blue-600 flex items-center justify-center text-xs font-bold border border-white">
              {earthquake.intensity}
            </div>
            <span>最大震度</span>
          </div>
        </div>
      )}
      
      {/* Legend */}
      <div className="absolute bottom-2 right-2 z-[1000] bg-black/80 text-white px-2 py-1 rounded text-xs space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 relative">
            <svg width="16" height="16" viewBox="0 0 16 16">
              <line x1="3" y1="3" x2="13" y2="13" stroke="#ff0000" strokeWidth="2"/>
              <line x1="13" y1="3" x2="3" y2="13" stroke="#ff0000" strokeWidth="2"/>
            </svg>
          </div>
          <span>震源地</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-600 border border-white text-[8px] flex items-center justify-center font-bold">
            1
          </div>
          <span>震度</span>
        </div>
      </div>
    </div>
  );
};

export default DetailedEarthquakeMap;

