export interface TsunamiInfo {
  id: string;
  time: string;
  grade: string;
  immediate: boolean;
  areas: TsunamiArea[];
}

export interface TsunamiArea {
  name: string;
  grade: string;
  immediate?: boolean;
}

export interface P2PApiResponse {
  id: string;
  time: string;
  tsunami?: {
    grade: string;
    immediate: boolean;
    areas: TsunamiArea[];
  };
}

export interface EarthquakeInfo {
  id: string;
  time: string;
  magnitude: number;
  depth: number;
  location: string;
  maxIntensity: string;
  tsunami: boolean;
}

export interface DisasterAlert {
  id: string;
  type: 'earthquake' | 'tsunami' | 'flood' | 'typhoon' | 'landslide';
  severity: 'minor' | 'moderate' | 'major' | 'severe';
  location: string;
  time: string;
  description: string;
  status: 'active' | 'resolved' | 'monitoring';
}

export interface WeatherAlert {
  id: string;
  type: string;
  area: string;
  severity: string;
  description: string;
  validFrom: string;
  validTo: string;
} 