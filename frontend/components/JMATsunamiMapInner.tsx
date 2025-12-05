"use client";

import React from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
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
  lat: 37.979,
  lng: 135.0
};

interface JMATsunamiMapInnerProps {
  children?: React.ReactNode;
}

const JMATsunamiMapInner: React.FC<JMATsunamiMapInnerProps> = ({ children }) => {
  return (
    <MapContainer
      center={[JAPAN_CENTER.lat, JAPAN_CENTER.lng]}
      zoom={5}
      style={{ height: '100%', width: '100%' }}
      className="z-0"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Leaflet'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {children}
    </MapContainer>
  );
};

export default JMATsunamiMapInner;


