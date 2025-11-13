import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default markers in react-leaflet
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: '/leaflet/marker-icon-2x.png',
    iconUrl: '/leaflet/marker-icon.png',
    shadowUrl: '/leaflet/marker-shadow.png',
  });
}

const JAPAN_CENTER = {
  lat: 36.5,
  lng: 138.0
};

interface EarthquakeData {
  id: string;
  time: string;
  location: string;
  magnitude: number;
  depth: number;
  latitude: number;
  longitude: number;
  intensity: string;
  tsunami?: boolean;
}

interface PGADataPoint {
  id: string;
  latitude: number;
  longitude: number;
  pga: number; // Peak Ground Acceleration in gal
  location: string;
}

interface JapanPGAMapComponentProps {
  earthquakes: EarthquakeData[];
  pgaData: PGADataPoint[];
}

// PGA Color Scale (matching the reference image)
const getPGAColor = (pga: number): string => {
  if (pga >= 1000) return '#800000'; // Dark Red
  if (pga >= 500) return '#ff0000';  // Red
  if (pga >= 200) return '#ff4500';  // Orange-Red
  if (pga >= 100) return '#ff8c00';  // Dark Orange
  if (pga >= 50) return '#ffa500';   // Orange
  if (pga >= 20) return '#ffd700';   // Gold
  if (pga >= 10) return '#ffff00';   // Yellow
  if (pga >= 5) return '#adff2f';    // Green-Yellow
  if (pga >= 2) return '#7fff00';    // Chartreuse
  if (pga >= 1) return '#00ff00';    // Green
  if (pga >= 0.5) return '#00ffff';  // Cyan
  if (pga >= 0.2) return '#00bfff';  // Deep Sky Blue
  if (pga >= 0.1) return '#4169e1';  // Royal Blue
  if (pga >= 0.05) return '#0000ff'; // Blue
  return '#00008b'; // Dark Blue
};

const getPGARadius = (pga: number): number => {
  // Scale radius based on PGA value
  if (pga >= 100) return 8;
  if (pga >= 50) return 7;
  if (pga >= 20) return 6;
  if (pga >= 10) return 5;
  if (pga >= 5) return 4;
  if (pga >= 1) return 3;
  return 2;
};

// PGA Scale Legend Component
const PGAScaleLegend: React.FC = () => {
  const scaleSteps = [
    { value: 1000, label: '1000' },
    { value: 500, label: '500' },
    { value: 200, label: '200' },
    { value: 100, label: '100' },
    { value: 50, label: '50' },
    { value: 20, label: '20' },
    { value: 10, label: '10' },
    { value: 5, label: '5' },
    { value: 2, label: '2' },
    { value: 1, label: '1' },
    { value: 0.5, label: '0.5' },
    { value: 0.2, label: '0.2' },
    { value: 0.1, label: '0.1' },
    { value: 0.05, label: '0.05' },
    { value: 0.01, label: '0.01' },
  ];

  return (
    <div className="absolute top-20 right-4 z-[1000] bg-white/90 rounded-lg shadow-lg p-3">
      <div className="text-sm font-bold text-center mb-2 text-gray-800">
        PGA[gal]
      </div>
      <div className="flex flex-col-reverse gap-0.5">
        {scaleSteps.map((step) => (
          <div key={step.value} className="flex items-center gap-2">
            <div
              className="w-6 h-4 border border-gray-300"
              style={{ backgroundColor: getPGAColor(step.value) }}
            />
            <div className="text-xs font-mono text-gray-800 w-12 text-right">
              {step.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const JapanPGAMapComponent: React.FC<JapanPGAMapComponentProps> = ({ 
  earthquakes, 
  pgaData 
}) => {
  // Find max PGA value
  const maxPGA = pgaData.length > 0 
    ? Math.max(...pgaData.map(p => p.pga))
    : 0;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[JAPAN_CENTER.lat, JAPAN_CENTER.lng]}
        zoom={6}
        className="h-full w-full"
        style={{ height: '100%', width: '100%', backgroundColor: '#1a1a2e' }}
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* PGA Data Points */}
        {pgaData.map((point) => (
          <CircleMarker
            key={point.id}
            center={[point.latitude, point.longitude]}
            radius={getPGARadius(point.pga)}
            pathOptions={{
              color: getPGAColor(point.pga),
              fillColor: getPGAColor(point.pga),
              fillOpacity: 0.7,
              weight: 1,
              opacity: 0.8
            }}
          >
            <Popup>
              <div className="p-2 min-w-[150px]">
                <div className="font-bold text-sm">{point.location}</div>
                <div className="text-xs mt-1">
                  <div>PGA: <span className="font-bold">{point.pga.toFixed(2)} gal</span></div>
                  <div className="text-gray-600">
                    位置: {point.latitude.toFixed(3)}°N, {point.longitude.toFixed(3)}°E
                  </div>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* PGA Scale Legend */}
      <PGAScaleLegend />

      {/* Current Max PGA Display */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-black/80 text-white px-4 py-2 rounded shadow-lg">
        <div className="text-lg font-bold">
          {maxPGA.toFixed(1)} gal
        </div>
        <div className="text-xs text-gray-300">最大 PGA</div>
      </div>

      {/* Leaflet Attribution */}
      <div className="absolute bottom-2 right-2 z-[999] text-xs text-gray-600 bg-white/70 px-2 py-1 rounded">
        Leaflet | © OpenStreetMap contributors
      </div>
    </div>
  );
};

export default JapanPGAMapComponent;

