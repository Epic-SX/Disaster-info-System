"use client";

import { Suspense, useState, useEffect } from 'react';
import JapanMonitorMap from '@/components/JapanMonitorMap';

// Loading component
const LoadingScreen = () => (
  <div className="h-screen w-screen flex items-center justify-center bg-gray-900">
    <div className="text-center text-white">
      <div className="text-6xl mb-4 animate-pulse">🗾</div>
      <div className="text-2xl font-bold">リアルタイム災害監視システム</div>
      <div className="text-lg mt-2">マップを読み込み中...</div>
    </div>
  </div>
);

// Client-only wrapper component
function ClientOnlyComponent({ children }: { children: React.ReactNode }) {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  if (!hasMounted) {
    return <LoadingScreen />;
  }

  return <>{children}</>;
}

export default function JapanMonitorPage() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <ClientOnlyComponent>
        <Suspense fallback={<LoadingScreen />}>
          <JapanMonitorMap />
        </Suspense>
      </ClientOnlyComponent>
    </div>
  );
}

