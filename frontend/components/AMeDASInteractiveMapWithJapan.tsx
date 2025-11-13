'use client'

import React, { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wind, Thermometer, Droplets, X, RefreshCw, MapPin } from 'lucide-react'

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
)
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
)
const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
)
const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
)

// Station coordinates will be loaded from API

interface WindDataPoint {
  location: string
  speed: string
  direction: string
  gusts: string
  status: string
  timestamp: string
  temperature?: string
  humidity?: string
  lat?: number
  lng?: number
}

// Custom wind arrow icon component
const WindArrowIcon = ({ direction, speed, color }: { direction: string; speed: string; color: string }) => {
  const getWindDirectionAngle = (dir: string): number => {
    const directionMap: Record<string, number> = {
      '北': 180, '北北東': 202.5, '北東': 225, '東北東': 247.5,
      '東': 270, '東南東': 292.5, '南東': 315, '南南東': 337.5,
      '南': 0, '南南西': 22.5, '南西': 45, '西南西': 67.5,
      '西': 90, '西北西': 112.5, '北西': 135, '北北西': 157.5,
    }
    return directionMap[dir] || 0
  }

  const angle = getWindDirectionAngle(direction)
  const speedNum = parseFloat(speed.replace(/[^\d.]/g, ''))
  const size = Math.max(30, Math.min(50, 30 + speedNum * 2))

  return (
    <div
      style={{
        width: `${size}px`,
        height: `${size}px`,
        transform: `rotate(${angle}deg)`,
        transformOrigin: 'center',
      }}
    >
      <svg viewBox="0 0 24 24" fill={color} className="drop-shadow-lg">
        <path d="M12 2L4 12h6v10h4V12h6L12 2z" />
      </svg>
    </div>
  )
}

// Create custom divIcon for Leaflet - Simplified design for better visibility
const createWindArrowDivIcon = async (direction: string, speed: string, color: string) => {
  if (typeof window === 'undefined') return null
  
  // Dynamically import leaflet to avoid require()
  const L = await import('leaflet')
  const angle = (() => {
    const directionMap: Record<string, number> = {
      '北': 180, '北北東': 202.5, '北東': 225, '東北東': 247.5,
      '東': 270, '東南東': 292.5, '南東': 315, '南南東': 337.5,
      '南': 0, '南南西': 22.5, '南西': 45, '西南西': 67.5,
      '西': 90, '西北西': 112.5, '北西': 135, '北北西': 157.5,
    }
    return directionMap[direction] || 0
  })()
  
  const speedNum = parseFloat(speed.replace(/[^\d.]/g, ''))
  // Smaller size for better visibility when showing many stations
  const size = Math.max(16, Math.min(28, 16 + speedNum * 1.2))
  
  return L.divIcon({
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        transform: rotate(${angle}deg);
        transform-origin: center;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <svg viewBox="0 0 24 24" fill="${color}" style="width: 100%; height: 100%; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.4));">
          <path d="M12 3L6 12h4v9h4v-9h4L12 3z" stroke="rgba(0,0,0,0.3)" stroke-width="0.5"/>
        </svg>
      </div>
    `,
    className: 'wind-arrow-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

const AMeDASInteractiveMapWithJapan: React.FC = () => {
  const [windData, setWindData] = useState<WindDataPoint[]>([])
  const [selectedStation, setSelectedStation] = useState<WindDataPoint | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const [isMounted, setIsMounted] = useState(false)
  const [leafletIcons, setLeafletIcons] = useState<Map<string, any>>(new Map())
  const [stationCoordinates, setStationCoordinates] = useState<Record<string, { lat: number; lng: number }>>({})

  useEffect(() => {
    setIsMounted(true)
    // Fetch station coordinates on mount
    fetchStationCoordinates()
  }, [])

  // Fetch station coordinates from API
  const fetchStationCoordinates = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/weather/amedas/station-coordinates`)
      if (response.ok) {
        const coords = await response.json()
        setStationCoordinates(coords)
        console.log(`Loaded coordinates for ${Object.keys(coords).length} stations`)
      }
    } catch (err) {
      console.error('Error fetching station coordinates:', err)
    }
  }

  // Get arrow color based on wind speed - white for normal, colors for alerts
  const getArrowColor = (speed: string): string => {
    const speedNum = parseFloat(speed.replace(/[^\d.]/g, ''))
    if (speedNum >= 15) return '#ef4444' // Red - Strong wind
    if (speedNum >= 10) return '#f97316' // Orange - Moderate wind
    if (speedNum >= 7) return '#60a5fa' // Light blue - Notable wind
    return '#ffffff' // White - Normal wind
  }

  // Fetch wind data
  const fetchWindData = React.useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/weather/wind`)
      if (response.ok) {
        const data: WindDataPoint[] = await response.json()
        
        // Add coordinates from stationCoordinates state (includes all stations)
        const dataWithCoords = data.map(point => ({
          ...point,
          lat: stationCoordinates[point.location]?.lat,
          lng: stationCoordinates[point.location]?.lng,
        })).filter(point => point.lat && point.lng)
        
        console.log(`Displaying ${dataWithCoords.length} stations on map (out of ${data.length} total)`)
        
        setWindData(dataWithCoords)
        setLastUpdate(new Date().toLocaleTimeString('ja-JP'))
        setLoading(false)
        
        // Pre-generate icons for all stations
        const iconPromises = dataWithCoords.map(async (station) => {
          const color = getArrowColor(station.speed)
          const icon = await createWindArrowDivIcon(station.direction, station.speed, color)
          return { key: `${station.location}-${station.speed}-${station.direction}`, icon }
        })
        
        const icons = await Promise.all(iconPromises)
        const iconMap = new Map(icons.map(({ key, icon }) => [key, icon]))
        setLeafletIcons(iconMap)
      }
    } catch (err) {
      console.error('Error fetching wind data:', err)
      setLoading(false)
    }
  }, [stationCoordinates])

  useEffect(() => {
    fetchWindData()
    const interval = setInterval(fetchWindData, 60000)
    return () => clearInterval(interval)
  }, [fetchWindData])

  const getWindDirectionAngle = (direction: string): number => {
    const directionMap: Record<string, number> = {
      '北': 180, '北北東': 202.5, '北東': 225, '東北東': 247.5,
      '東': 270, '東南東': 292.5, '南東': 315, '南南東': 337.5,
      '南': 0, '南南西': 22.5, '南西': 45, '西南西': 67.5,
      '西': 90, '西北西': 112.5, '北西': 135, '北北西': 157.5,
    }
    return directionMap[direction] || 0
  }

  if (!isMounted) {
    return (
      <Card className="bg-gradient-to-br from-slate-900 to-blue-900 text-white border-blue-700">
        <CardHeader>
          <CardTitle>Loading map...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[600px] flex items-center justify-center">
            <div className="animate-spin text-4xl">🌪️</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-blue-900 text-white border-blue-700">
      <CardHeader className="bg-gradient-to-r from-green-600 to-emerald-600">
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wind className="h-6 w-6" />
            🗾 AMeDAS気象観測システム - 日本地図表示
          </span>
          <div className="flex items-center gap-3">
            <Badge className="bg-white text-green-600 text-xs font-bold animate-pulse">
              <span className="w-2 h-2 bg-green-600 rounded-full mr-1"></span>
              LIVE配信
            </Badge>
            {lastUpdate && (
              <span className="text-xs text-green-100">
                更新: {lastUpdate}
              </span>
            )}
            <button
              onClick={fetchWindData}
              className="p-2 hover:bg-green-700 rounded-lg transition-colors"
              title="データを更新"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </CardTitle>
        <div className="text-sm mt-1 text-green-100">
          📡 毎時更新（JMAからスクレイピング） • 全国{windData.length}観測所データ表示中
        </div>
      </CardHeader>

      <CardContent className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map Area */}
          <div className="lg:col-span-2">
            <div className="relative rounded-lg border-2 border-blue-700 overflow-hidden" style={{ height: '600px' }}>
              <MapContainer
                center={[37.5, 138.0]}
                zoom={5}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                {windData.map((station, index) => {
                  if (!station.lat || !station.lng) return null
                  
                  const iconKey = `${station.location}-${station.speed}-${station.direction}`
                  const icon = leafletIcons.get(iconKey)
                  
                  if (!icon) return null
                  
                  return (
                    <Marker
                      key={`${station.location}-${index}`}
                      position={[station.lat, station.lng]}
                      icon={icon}
                      eventHandlers={{
                        click: () => setSelectedStation(station)
                      }}
                    >
                      <Popup>
                        <div className="text-gray-900">
                          <h3 className="font-bold text-lg mb-2">{station.location}</h3>
                          <div className="space-y-1 text-sm">
                            <p><strong>風速:</strong> {station.speed}</p>
                            <p><strong>風向:</strong> {station.direction}</p>
                            <p><strong>最大瞬間風速:</strong> {station.gusts}</p>
                            {station.temperature && <p><strong>気温:</strong> {station.temperature}</p>}
                            {station.humidity && <p><strong>湿度:</strong> {station.humidity}</p>}
                          </div>
                        </div>
                      </Popup>
                    </Marker>
                  )
                })}
              </MapContainer>

              {/* Legend */}
              <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-sm rounded-lg p-3 text-xs z-[1000]">
                <div className="font-bold mb-2">風速凡例</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded border border-gray-400" style={{ backgroundColor: '#ffffff' }}></div>
                    <span>0-7 m/s: 通常</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#60a5fa' }}></div>
                    <span>7-10 m/s: やや強い</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#f97316' }}></div>
                    <span>10-15 m/s: 強風注意</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded animate-pulse" style={{ backgroundColor: '#ef4444' }}></div>
                    <span>15+ m/s: 警戒</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Station Detail Panel */}
          <div className="lg:col-span-1">
            {selectedStation ? (
              <div className="bg-gradient-to-br from-slate-800 to-slate-700 border-2 border-cyan-500 rounded-lg p-4 sticky top-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-lg text-white flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-red-500" />
                    {selectedStation.location}
                  </h3>
                  <button
                    onClick={() => setSelectedStation(null)}
                    className="p-1 hover:bg-slate-600 rounded transition-colors"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <Badge 
                  className={`text-xs font-bold mb-4 ${
                    selectedStation.status === 'normal' ? 'bg-green-600' :
                    selectedStation.status === 'moderate' ? 'bg-yellow-600' :
                    'bg-gray-600'
                  }`}
                >
                  {selectedStation.status === 'normal' ? '正常' : selectedStation.status}
                </Badge>

                <div className="mb-4 text-center bg-blue-900/50 rounded-lg p-4">
                  <div className="text-4xl font-bold text-cyan-300 mb-1">
                    {selectedStation.speed}
                  </div>
                  <div className="text-sm text-cyan-200">現在の風速</div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-blue-900/50 rounded-lg p-3 text-center">
                    <div className="text-blue-200 text-xs mb-1">風向</div>
                    <div className="font-bold text-white text-lg">{selectedStation.direction}</div>
                    <div 
                      className="text-2xl mt-1"
                      style={{ transform: `rotate(${getWindDirectionAngle(selectedStation.direction)}deg)` }}
                    >
                      ↑
                    </div>
                  </div>
                  <div className="bg-orange-900/50 rounded-lg p-3 text-center">
                    <div className="text-orange-200 text-xs mb-1">最大瞬間風速</div>
                    <div className="font-bold text-white text-lg">{selectedStation.gusts}</div>
                  </div>
                </div>

                {(selectedStation.temperature || selectedStation.humidity) && (
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {selectedStation.temperature && (
                      <div className="bg-red-900/50 rounded-lg p-3 text-center">
                        <div className="text-red-200 text-xs mb-1 flex items-center justify-center gap-1">
                          <Thermometer className="h-3 w-3" />
                          気温
                        </div>
                        <div className="font-bold text-white text-lg">{selectedStation.temperature}</div>
                      </div>
                    )}
                    {selectedStation.humidity && (
                      <div className="bg-purple-900/50 rounded-lg p-3 text-center">
                        <div className="text-purple-200 text-xs mb-1 flex items-center justify-center gap-1">
                          <Droplets className="h-3 w-3" />
                          湿度
                        </div>
                        <div className="font-bold text-white text-lg">{selectedStation.humidity}</div>
                      </div>
                    )}
                  </div>
                )}

                {parseFloat(selectedStation.speed.replace(/[^\d.]/g, '')) > 15 && (
                  <div className="bg-red-600 text-white p-3 rounded-lg text-center text-sm font-bold animate-pulse">
                    ⚠️ 強風注意
                  </div>
                )}

                <div className="mt-4 text-xs text-slate-400 text-center">
                  地図上のマーカーをクリックして観測所を選択
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 border-2 border-slate-600 rounded-lg p-8 text-center sticky top-4">
                <MapPin className="h-16 w-16 text-slate-500 mx-auto mb-4" />
                <p className="text-slate-400 mb-2">観測所を選択してください</p>
                <p className="text-xs text-slate-500">
                  地図上の風向マーカーをクリックすると<br/>詳細な気象データが表示されます
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Statistics */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-white">{windData.length}</div>
            <div className="text-blue-100 text-sm">監視地点数</div>
          </div>
          <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-white">
              {windData.length > 0 ? Math.max(...windData.map(d => parseFloat(d.speed.replace(/[^\d.]/g, '')) || 0)).toFixed(1) : '0'}
            </div>
            <div className="text-green-100 text-sm">最大風速 (m/s)</div>
          </div>
          <div className="bg-gradient-to-r from-orange-600 to-red-600 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-white">
              {windData.filter(d => parseFloat(d.speed.replace(/[^\d.]/g, '')) > 15).length}
            </div>
            <div className="text-orange-100 text-sm">強風警戒地点</div>
          </div>
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-white">
              {windData.filter(d => d.status === 'normal').length}
            </div>
            <div className="text-purple-100 text-sm">正常稼働地点</div>
          </div>
        </div>
      </CardContent>

      <style jsx global>{`
        .wind-arrow-icon {
          background: transparent !important;
          border: none !important;
          cursor: pointer !important;
          transition: transform 0.2s ease;
        }
        .wind-arrow-icon:hover {
          transform: scale(1.2);
        }
        .leaflet-popup-content-wrapper {
          border-radius: 8px;
        }
        .leaflet-marker-icon svg {
          pointer-events: none;
        }
      `}</style>
    </Card>
  )
}

export default AMeDASInteractiveMapWithJapan

