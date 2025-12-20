"use client";

import { Suspense, useState, useEffect } from 'react';
import TechnicalMonitorDashboard from '@/components/TechnicalMonitorDashboard';

// Loading component
const LoadingScreen = () => (
  <div className="h-screen w-screen flex items-center justify-center bg-[#0a0e1a]">
    <div className="text-center text-white">
      <div className="text-6xl mb-4 animate-pulse">🌊</div>
      <div className="text-2xl font-bold">災害監視システム起動中</div>
      <div className="text-lg mt-2">Technical Monitor Loading...</div>
      <div className="mt-4">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
      </div>
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

export default function TechnicalMonitorPage() {
  return (
    <div className="fixed inset-0 overflow-hidden bg-[#050914]">
      <ClientOnlyComponent>
        <Suspense fallback={<LoadingScreen />}>
          <TechnicalMonitorDashboard />
        </Suspense>
      </ClientOnlyComponent>
    </div>
  );
}

