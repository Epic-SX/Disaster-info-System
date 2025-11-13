'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Wind, Thermometer, Droplets, X, RefreshCw, MapPin } from 'lucide-react'

// AMeDAS Station Coordinates (Major Stations - will be expanded)
const STATION_COORDINATES: Record<string, { lat: number; lng: number }> = {
  '宗谷岬': { lat: 45.5231, lng: 141.9408 },
  '稚内': { lat: 45.4153, lng: 141.6739 },
  '礼文': { lat: 45.4606, lng: 141.0442 },
  '声問': { lat: 45.3258, lng: 141.8167 },
  '浜鬼志別': { lat: 45.1267, lng: 142.3069 },
  '本泊': { lat: 45.0583, lng: 142.1517 },
  '沼川': { lat: 45.0728, lng: 141.8831 },
  '宗谷': { lat: 45.4739, lng: 142.0406 },
  '豊富': { lat: 45.1022, lng: 141.7778 },
  '中頓別': { lat: 44.9589, lng: 142.2714 },
  '浜頓別': { lat: 45.1189, lng: 142.3606 },
  '枝幸': { lat: 44.9394, lng: 142.5786 },
  '雄武': { lat: 44.5811, lng: 142.9597 },
  '興部': { lat: 44.4028, lng: 143.1100 },
  '紋別': { lat: 44.3547, lng: 143.3544 },
  '紋別小向': { lat: 44.3250, lng: 143.2944 },
  '西興部': { lat: 44.3317, lng: 142.8486 },
  '滝上': { lat: 44.1456, lng: 142.8925 },
  '旭川': { lat: 43.7706, lng: 142.3647 },
  '札幌': { lat: 43.0642, lng: 141.3469 },
  '函館': { lat: 41.7689, lng: 140.7289 },
  '青森': { lat: 40.8244, lng: 140.7400 },
  '盛岡': { lat: 39.7008, lng: 141.1536 },
  '仙台': { lat: 38.2603, lng: 140.8722 },
  '秋田': { lat: 39.7186, lng: 140.1028 },
  '山形': { lat: 38.2553, lng: 140.3394 },
  '福島': { lat: 37.7608, lng: 140.4750 },
  '水戸': { lat: 36.3833, lng: 140.4686 },
  '宇都宮': { lat: 36.5497, lng: 139.8833 },
  '前橋': { lat: 36.3997, lng: 139.0622 },
  'さいたま': { lat: 35.8617, lng: 139.6467 },
  '千葉': { lat: 35.6050, lng: 140.1233 },
  '東京': { lat: 35.6894, lng: 139.6917 },
  '横浜': { lat: 35.4436, lng: 139.6378 },
  '新潟': { lat: 37.9161, lng: 139.0364 },
  '富山': { lat: 36.6958, lng: 137.2117 },
  '金沢': { lat: 36.5944, lng: 136.6256 },
  '福井': { lat: 36.0614, lng: 136.2217 },
  '甲府': { lat: 35.6633, lng: 138.5683 },
  '長野': { lat: 36.6514, lng: 138.1811 },
  '岐阜': { lat: 35.4231, lng: 136.7614 },
  '静岡': { lat: 34.9756, lng: 138.3828 },
  '名古屋': { lat: 35.1814, lng: 136.9064 },
  '津': { lat: 34.7303, lng: 136.5081 },
  '大津': { lat: 35.0047, lng: 135.8686 },
  '京都': { lat: 35.0117, lng: 135.7681 },
  '大阪': { lat: 34.6937, lng: 135.5022 },
  '神戸': { lat: 34.6901, lng: 135.1955 },
  '奈良': { lat: 34.6851, lng: 135.8048 },
  '和歌山': { lat: 34.2331, lng: 135.1675 },
  '鳥取': { lat: 35.5036, lng: 134.2378 },
  '松江': { lat: 35.4722, lng: 133.0506 },
  '岡山': { lat: 34.6617, lng: 133.9181 },
  '広島': { lat: 34.3969, lng: 132.4597 },
  '下関': { lat: 33.9569, lng: 130.9233 },
  '徳島': { lat: 34.0658, lng: 134.5597 },
  '高松': { lat: 34.3428, lng: 134.0436 },
  '松山': { lat: 33.8414, lng: 132.7658 },
  '高知': { lat: 33.5597, lng: 133.5311 },
  '福岡': { lat: 33.5903, lng: 130.4017 },
  '佐賀': { lat: 33.2633, lng: 130.3008 },
  '長崎': { lat: 32.7442, lng: 129.8736 },
  '熊本': { lat: 32.8031, lng: 130.7078 },
  '大分': { lat: 33.2382, lng: 131.6125 },
  '宮崎': { lat: 31.9111, lng: 131.4203 },
  '鹿児島': { lat: 31.5603, lng: 130.5581 },
  '那覇': { lat: 26.2125, lng: 127.6792 },
}

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

const AMeDASInteractiveMap: React.FC = () => {
  const [windData, setWindData] = useState<WindDataPoint[]>([])
  const [selectedStation, setSelectedStation] = useState<WindDataPoint | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const mapRef = useRef<HTMLDivElement>(null)
  const [mapDimensions, setMapDimensions] = useState({ width: 0, height: 0 })

  // Japan map bounds (approximate)
  const JAPAN_BOUNDS = {
    north: 45.5,
    south: 24,
    west: 122,
    east: 154
  }

  // Convert lat/lng to pixel coordinates on the map
  const latLngToPixel = (lat: number, lng: number) => {
    const latPercent = (JAPAN_BOUNDS.north - lat) / (JAPAN_BOUNDS.north - JAPAN_BOUNDS.south)
    const lngPercent = (lng - JAPAN_BOUNDS.west) / (JAPAN_BOUNDS.east - JAPAN_BOUNDS.west)
    
    return {
      x: lngPercent * mapDimensions.width,
      y: latPercent * mapDimensions.height
    }
  }

  // Get wind direction as rotation angle
  const getWindDirectionAngle = (direction: string): number => {
    const directionMap: Record<string, number> = {
      '北': 180,
      '北北東': 202.5,
      '北東': 225,
      '東北東': 247.5,
      '東': 270,
      '東南東': 292.5,
      '南東': 315,
      '南南東': 337.5,
      '南': 0,
      '南南西': 22.5,
      '南西': 45,
      '西南西': 67.5,
      '西': 90,
      '西北西': 112.5,
      '北西': 135,
      '北北西': 157.5,
    }
    return directionMap[direction] || 0
  }

  // Get arrow color based on wind speed
  const getArrowColor = (speed: string): string => {
    const speedNum = parseFloat(speed.replace(/[^\d.]/g, ''))
    if (speedNum >= 15) return '#ef4444' // Red for strong wind
    if (speedNum >= 10) return '#f97316' // Orange for moderate wind
    if (speedNum >= 5) return '#3b82f6' // Blue for light wind
    return '#60a5fa' // Light blue for calm
  }

  // Fetch wind data
  const fetchWindData = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/weather/wind`)
      if (response.ok) {
        const data: WindDataPoint[] = await response.json()
        
        // Add coordinates to wind data
        const dataWithCoords = data.map(point => ({
          ...point,
          lat: STATION_COORDINATES[point.location]?.lat,
          lng: STATION_COORDINATES[point.location]?.lng,
        })).filter(point => point.lat && point.lng) // Only include stations with coordinates
        
        setWindData(dataWithCoords)
        setLastUpdate(new Date().toLocaleTimeString('ja-JP'))
        setLoading(false)
      }
    } catch (err) {
      console.error('Error fetching wind data:', err)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWindData()
    const interval = setInterval(fetchWindData, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (mapRef.current) {
      const updateDimensions = () => {
        setMapDimensions({
          width: mapRef.current?.offsetWidth || 0,
          height: mapRef.current?.offsetHeight || 0
        })
      }
      updateDimensions()
      window.addEventListener('resize', updateDimensions)
      return () => window.removeEventListener('resize', updateDimensions)
    }
  }, [])

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-blue-900 text-white border-blue-700">
      <CardHeader className="bg-gradient-to-r from-green-600 to-emerald-600">
        <CardTitle className="text-xl font-bold flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wind className="h-6 w-6" />
            🗾 AMeDAS気象観測システム稼働中
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
            <div className="relative bg-blue-950 rounded-lg border-2 border-blue-700 overflow-hidden" style={{ height: '600px' }}>
              {/* Map background */}
              <div
                ref={mapRef}
                className="absolute inset-0 bg-gradient-to-br from-blue-900 to-cyan-800"
                style={{
                  backgroundImage: 'radial-gradient(circle at 30% 50%, rgba(59, 130, 246, 0.3) 0%, transparent 50%)',
                }}
              >
                {/* Grid lines */}
                <svg className="absolute inset-0 w-full h-full opacity-20">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <React.Fragment key={`grid-${i}`}>
                      <line
                        x1="0"
                        y1={`${(i * 10)}%`}
                        x2="100%"
                        y2={`${(i * 10)}%`}
                        stroke="white"
                        strokeWidth="0.5"
                      />
                      <line
                        x1={`${(i * 10)}%`}
                        y1="0"
                        x2={`${(i * 10)}%`}
                        y2="100%"
                        stroke="white"
                        strokeWidth="0.5"
                      />
                    </React.Fragment>
                  ))}
                </svg>

                {/* Wind direction arrows */}
                {windData.map((station, index) => {
                  if (!station.lat || !station.lng) return null
                  
                  const pos = latLngToPixel(station.lat, station.lng)
                  const angle = getWindDirectionAngle(station.direction)
                  const color = getArrowColor(station.speed)
                  const speedNum = parseFloat(station.speed.replace(/[^\d.]/g, ''))
                  const arrowSize = Math.max(20, Math.min(40, 20 + speedNum * 1.5))
                  
                  return (
                    <div
                      key={`station-${station.location}-${index}`}
                      className="absolute cursor-pointer transition-all duration-200 hover:scale-150 hover:z-50"
                      style={{
                        left: `${pos.x}px`,
                        top: `${pos.y}px`,
                        transform: 'translate(-50%, -50%)',
                      }}
                      onClick={() => setSelectedStation(station)}
                      title={`${station.location}: ${station.speed} ${station.direction}`}
                    >
                      {/* Arrow */}
                      <div
                        className="relative"
                        style={{
                          width: `${arrowSize}px`,
                          height: `${arrowSize}px`,
                          transform: `rotate(${angle}deg)`,
                        }}
                      >
                        <svg
                          viewBox="0 0 24 24"
                          fill={color}
                          className="w-full h-full drop-shadow-lg"
                        >
                          <path d="M12 2L4 12h6v10h4V12h6L12 2z" />
                        </svg>
                      </div>
                      
                      {/* Station label (on hover) */}
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-1 bg-black/80 text-white px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
                        {station.location}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Legend */}
              <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-xs">
                <div className="font-bold mb-2">風速凡例</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#60a5fa' }}></div>
                    <span>0-5 m/s: 穏やか</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#3b82f6' }}></div>
                    <span>5-10 m/s: 通常</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#f97316' }}></div>
                    <span>10-15 m/s: やや強い</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded animate-pulse" style={{ backgroundColor: '#ef4444' }}></div>
                    <span>15+ m/s: 強風</span>
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

                {/* Current Wind Speed */}
                <div className="mb-4 text-center bg-blue-900/50 rounded-lg p-4">
                  <div className="text-4xl font-bold text-cyan-300 mb-1">
                    {selectedStation.speed}
                  </div>
                  <div className="text-sm text-cyan-200">現在の風速</div>
                </div>

                {/* Wind Details */}
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

                {/* Temperature and Humidity */}
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

                {/* Warning */}
                {parseFloat(selectedStation.speed.replace(/[^\d.]/g, '')) > 15 && (
                  <div className="bg-red-600 text-white p-3 rounded-lg text-center text-sm font-bold animate-pulse">
                    ⚠️ 強風注意
                  </div>
                )}

                <div className="mt-4 text-xs text-slate-400 text-center">
                  クリックして別の観測所を選択
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 border-2 border-slate-600 rounded-lg p-8 text-center sticky top-4">
                <MapPin className="h-16 w-16 text-slate-500 mx-auto mb-4" />
                <p className="text-slate-400 mb-2">観測所を選択してください</p>
                <p className="text-xs text-slate-500">
                  地図上の矢印をクリックすると<br/>詳細な気象データが表示されます
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
            <div className="text-green-100 text-sm">最大風速 (km/h)</div>
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
    </Card>
  )
}

export default AMeDASInteractiveMap

