"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import EarthquakeMonitor from "@/components/EarthquakeMonitor"
import TsunamiAlert from "@/components/TsunamiAlert"
import NewsAggregator from "@/components/NewsAggregator"
import LiveCameraFeeds from "@/components/LiveCameraFeeds"
import WindDataDisplay from "@/components/WindDataDisplay"
import { AlertTriangle, Camera, Clock, MapPin, Play, Zap, Wind, Droplets } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import DisasterMap from "@/components/DisasterMap"
import { YouTubePlayerSimple } from "@/components/YouTubePlayer"
import YouTubeChatDashboard from "@/components/YouTubeChatDashboard"
import SocialMediaDashboard from "@/components/SocialMediaDashboard"
import { YouTubePlayerHybrid } from '@/components/YouTubePlayer'
import { YouTubeLiveStreams } from '@/components/YouTubeLiveStreams';

export default function Home() {
  return (
    <main className="container mx-auto p-4 space-y-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2">🌊 災害情報システム</h1>
        <p className="text-muted-foreground">
          リアルタイム災害監視・YouTube Live Chat連携・SNS自動化システム
        </p>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">概要</TabsTrigger>
          <TabsTrigger value="youtube">YouTube Live</TabsTrigger>
          <TabsTrigger value="chat">チャット監視</TabsTrigger>
          <TabsTrigger value="news">ニュース・データ</TabsTrigger>
          <TabsTrigger value="monitoring">監視システム</TabsTrigger>
          <TabsTrigger value="social">SNS管理</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EarthquakeMonitor />
            <TsunamiAlert />
          </div>
          
          <DisasterMap />
          
          <div className="grid grid-cols-1 gap-6">
            <WindDataDisplay />
          </div>
        </TabsContent>

        <TabsContent value="youtube" className="space-y-6">
          <YouTubeLiveStreams />
          <div className="grid gap-6 md:grid-cols-2">
            <EarthquakeMonitor />
            <TsunamiAlert />
          </div>
        </TabsContent>

        <TabsContent value="chat" className="space-y-6">
          <YouTubeChatDashboard />
        </TabsContent>

        <TabsContent value="news" className="space-y-6">
          <NewsAggregator />
          <LiveCameraFeeds />
        </TabsContent>

        <TabsContent value="monitoring" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EarthquakeMonitor />
            <TsunamiAlert />
            <WindDataDisplay />
            <LiveCameraFeeds />
          </div>
          <DisasterMap />
        </TabsContent>

        <TabsContent value="social" className="space-y-6">
          <SocialMediaDashboard />
        </TabsContent>
      </Tabs>
    </main>
  )
}
