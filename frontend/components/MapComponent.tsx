import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup } from 'react-leaflet';
import { Badge } from "@/components/ui/badge";
import { Zap } from 'lucide-react';
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
  lat: 36.2048,
  lng: 138.2529
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

interface TsunamiInfo {
  id: string;
  location: string;
  level: string;
  time: string;
  latitude: number;
  longitude: number;
}

interface MapComponentProps {
  earthquakes: EarthquakeData[];
  tsunamis: TsunamiInfo[];
  onMapReady?: () => void;
}

const getMagnitudeColor = (magnitude: number) => {
  if (magnitude >= 7) return '#ff0000'; // Red for major earthquakes
  if (magnitude >= 6) return '#ff4500'; // Orange-red
  if (magnitude >= 5) return '#ff8c00'; // Orange
  if (magnitude >= 4) return '#ffd700'; // Gold
  if (magnitude >= 3) return '#9acd32'; // Yellow-green
  return '#32cd32'; // Green for minor earthquakes
};

const getMagnitudeRadius = (magnitude: number) => {
  return Math.max(magnitude * 5000, 10000); // Minimum 10km radius
};

const getIntensityLabel = (intensity: string) => {
  const intensityMap: { [key: string]: string } = {
    '1': '震度1',
    '2': '震度2',
    '3': '震度3',
    '4': '震度4',
    '5-': '震度5弱',
    '5+': '震度5強',
    '6-': '震度6弱',
    '6+': '震度6強',
    '7': '震度7'
  };
  return intensityMap[intensity] || `震度${intensity}`;
};

const formatTime = (timeString: string) => {
  const date = new Date(timeString);
  return date.toLocaleString('ja-JP', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const MapComponent: React.FC<MapComponentProps> = ({ earthquakes, tsunamis, onMapReady }) => {
  useEffect(() => {
    if (onMapReady) {
      onMapReady();
    }
  }, [onMapReady]);

  return (
    <MapContainer
      center={[JAPAN_CENTER.lat, JAPAN_CENTER.lng]}
      zoom={6}
      className="h-full w-full"
      style={{ height: '100%', width: '100%' }}
    >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
      
      {/* Earthquake markers */}
      {earthquakes.map((earthquake) => (
        <Circle
          key={earthquake.id}
          center={[earthquake.latitude, earthquake.longitude]}
          radius={getMagnitudeRadius(earthquake.magnitude)}
          pathOptions={{
            color: getMagnitudeColor(earthquake.magnitude),
            fillColor: getMagnitudeColor(earthquake.magnitude),
            fillOpacity: 0.3,
            weight: 2
          }}
        >
          <Popup>
            <div className="p-2 min-w-[200px]">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <Zap className="h-4 w-4" />
                地震情報
              </h3>
              <div className="space-y-1 mt-2">
                <p><strong>発生時刻:</strong> {formatTime(earthquake.time)}</p>
                <p><strong>震源地:</strong> {earthquake.location}</p>
                <p><strong>マグニチュード:</strong> M{earthquake.magnitude}</p>
                <p><strong>深度:</strong> {earthquake.depth}km</p>
                <p><strong>最大震度:</strong> {getIntensityLabel(earthquake.intensity)}</p>
                {earthquake.tsunami && (
                  <Badge className="bg-red-500 text-white">津波の心配あり</Badge>
                )}
              </div>
            </div>
          </Popup>
        </Circle>
      ))}

      {/* Tsunami markers */}
      {tsunamis.map((tsunami) => (
        <Marker
          key={tsunami.id}
          position={[tsunami.latitude, tsunami.longitude]}
        >
          <Popup>
            <div className="p-2 min-w-[200px]">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <div className="text-blue-600">🌊</div>
                津波情報
              </h3>
              <div className="space-y-1 mt-2">
                <p><strong>発生時刻:</strong> {formatTime(tsunami.time)}</p>
                <p><strong>地域:</strong> {tsunami.location}</p>
                <p><strong>レベル:</strong> {tsunami.level}</p>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default MapComponent; 