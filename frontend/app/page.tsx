"use client";

// Force dynamic rendering to avoid static generation issues
export const dynamic = 'force-dynamic';

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AlertTriangle, Camera, Clock, MapPin, Play, Zap, Wind, Droplets, Map } from "lucide-react"
import { Badge } from "@/components/ui/badge"
 import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Suspense, useState, useEffect } from 'react'
import NoSSR from "@/components/NoSSR"

// Regular imports with client-side rendering checks
import EarthquakeMonitor from "@/components/EarthquakeMonitor"
import TsunamiAlert from "@/components/TsunamiAlert"
import NewsAggregator from "@/components/NewsAggregator"
import LiveCameraFeeds from "@/components/LiveCameraFeeds"
import WindDataDisplay from "@/components/WindDataDisplay"
import AMeDASInteractiveMap from "@/components/AMeDASInteractiveMap"
import AMeDASInteractiveMapWithJapan from "@/components/AMeDASInteractiveMapWithJapan"
import DisasterMap from "@/components/DisasterMap"
import YouTubeChatDashboard from "@/components/YouTubeChatDashboard"
import YouTubeSearchDashboard from "@/components/YouTubeSearchDashboard"
import SocialMediaDashboard from "@/components/SocialMediaDashboard"
import YouTubeLiveStreams from '@/components/YouTubeLiveStreams'
import P2PEarthquakeMonitor from '@/components/P2PEarthquakeMonitor'
import dynamicImport from 'next/dynamic'

// Dynamically import map component to avoid SSR issues
const SeismicStationMapComponent = dynamicImport(() => import('@/components/SeismicStationMapComponent'), {
  ssr: false,
  loading: () => <Card><CardContent className="p-6"><div className="animate-pulse space-y-2"><div className="h-4 bg-muted rounded w-3/4"></div></div></CardContent></Card>
})

// Loading component
const LoadingCard = () => (
  <Card>
    <CardContent className="p-6">
      <div className="animate-pulse space-y-2">
        <div className="h-4 bg-muted rounded w-3/4"></div>
        <div className="h-4 bg-muted rounded w-1/2"></div>
      </div>
    </CardContent>
  </Card>
)

// Client-only wrapper component
function ClientOnlyComponent({ children }: { children: React.ReactNode }) {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  if (!hasMounted) {
    return <LoadingCard />;
  }

  return <>{children}</>;
}

export default function Home() {
  return (
    <main className="container mx-auto p-4 space-y-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2">🌊 災害情報システム</h1>
        <p className="text-muted-foreground">
          リアルタイム災害監視・YouTube Live Chat連携・SNS自動化システム
        </p>
        <div className="mt-4 flex gap-4 justify-center">
          <a 
            href="/japan-monitor"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium h-10 px-6 bg-red-600 hover:bg-red-700 text-white cursor-pointer transition-colors shadow-sm"
          >
            <Map className="mr-2 h-5 w-5" />
            日本全国監視マップ (フルスクリーン)
          </a>
          <a 
            href="/technical-monitor"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium h-10 px-6 bg-blue-600 hover:bg-blue-700 text-white cursor-pointer transition-colors shadow-sm"
          >
            <Zap className="mr-2 h-5 w-5" />
            テクニカル監視システム (フルスクリーン)
          </a>
        </div>
      </div>

      <NoSSR fallback={<LoadingCard />}>
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="overview">概要</TabsTrigger>
            <TabsTrigger value="p2p">P2P地震情報</TabsTrigger>
            <TabsTrigger value="youtube">YouTube Live</TabsTrigger>
            <TabsTrigger value="chat">チャット監視</TabsTrigger>
            <TabsTrigger value="news">ニュース・データ</TabsTrigger>
            <TabsTrigger value="monitoring">監視システム</TabsTrigger>
            <TabsTrigger value="social">SNS管理</TabsTrigger>
          </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ClientOnlyComponent>
              <EarthquakeMonitor />
            </ClientOnlyComponent>
            <ClientOnlyComponent>
              <TsunamiAlert />
            </ClientOnlyComponent>
          </div>
          
          <ClientOnlyComponent>
            <DisasterMap />
          </ClientOnlyComponent>
          
          <div className="grid grid-cols-1 gap-6">
            <ClientOnlyComponent>
              <AMeDASInteractiveMapWithJapan />
            </ClientOnlyComponent>
          </div>
        </TabsContent>

        <TabsContent value="p2p" className="space-y-6">
          <ClientOnlyComponent>
            <P2PEarthquakeMonitor />
          </ClientOnlyComponent>
        </TabsContent>

        <TabsContent value="youtube" className="space-y-6">
          <ClientOnlyComponent>
            <YouTubeSearchDashboard />
          </ClientOnlyComponent>
          <ClientOnlyComponent>
            <YouTubeLiveStreams />
          </ClientOnlyComponent>
          <div className="grid gap-6 md:grid-cols-2">
            <ClientOnlyComponent>
              <EarthquakeMonitor />
            </ClientOnlyComponent>
            <ClientOnlyComponent>
              <TsunamiAlert />
            </ClientOnlyComponent>
          </div>
        </TabsContent>

        <TabsContent value="chat" className="space-y-6">
          <ClientOnlyComponent>
            <YouTubeChatDashboard />
          </ClientOnlyComponent>
        </TabsContent>

        <TabsContent value="news" className="space-y-6">
          <ClientOnlyComponent>
            <NewsAggregator />
          </ClientOnlyComponent>
          <ClientOnlyComponent>
            <LiveCameraFeeds />
          </ClientOnlyComponent>
        </TabsContent>

        <TabsContent value="monitoring" className="space-y-6">
          <div className="grid grid-cols-1 gap-6">
            <ClientOnlyComponent>
              <AMeDASInteractiveMapWithJapan />
            </ClientOnlyComponent>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ClientOnlyComponent>
              <EarthquakeMonitor />
            </ClientOnlyComponent>
            <ClientOnlyComponent>
              <TsunamiAlert />
            </ClientOnlyComponent>
            <ClientOnlyComponent>
              <WindDataDisplay />
            </ClientOnlyComponent>
            <ClientOnlyComponent>
              <LiveCameraFeeds />
            </ClientOnlyComponent>
          </div>
          
          {/* Seismic Station Monitoring Map */}
          <ClientOnlyComponent>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  地震観測点リアルタイムマップ
                </CardTitle>
                <CardDescription>
                  全国の地震観測点における地盤加速度 (PGA) をリアルタイム表示
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-[600px] w-full">
                  <SeismicStationMapComponent />
                </div>
              </CardContent>
            </Card>
          </ClientOnlyComponent>
          
          <ClientOnlyComponent>
            <DisasterMap />
          </ClientOnlyComponent>
        </TabsContent>

        <TabsContent value="social" className="space-y-6">
          <ClientOnlyComponent>
            <SocialMediaDashboard />
          </ClientOnlyComponent>
        </TabsContent>
        </Tabs>
      </NoSSR>
    </main>
  )
}
