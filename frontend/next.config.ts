import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  
  // Disable static optimization to avoid webpack runtime issues
  output: 'standalone',
  trailingSlash: false,
  
  // Cross-origin development configuration
  allowedDevOrigins: ['49.212.176.130'],
  
  // Handle unhandled promise rejections during build
  onDemandEntries: {
    // period (in ms) where the server will keep pages in the buffer
    maxInactiveAge: 25 * 1000,
    // number of pages that should be kept simultaneously without being disposed
    pagesBufferLength: 2,
  },
  
  // API rewrites for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  
  // Server external packages to fix build issues
  serverExternalPackages: ['leaflet'],
  
  // Simplified webpack configuration
  webpack: (config, { isServer }) => {
    // Fix for client-side modules
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
      };
    }
    
    // Add global error handler for unhandled promise rejections
    config.plugins = config.plugins || [];
    config.plugins.push(
      new (require('webpack')).DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
      })
    );
    
    // Add error handling for webpack runtime issues
    config.optimization = {
      ...config.optimization,
      splitChunks: {
        ...config.optimization?.splitChunks,
        cacheGroups: {
          ...config.optimization?.splitChunks?.cacheGroups,
          default: {
            ...config.optimization?.splitChunks?.cacheGroups?.default,
            minChunks: 1,
          },
        },
      },
    };
    
    return config;
  },
  
  // Environment variables validation
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL,
  },
  
  // Static assets headers
  async headers() {
    return [
      {
        source: '/favicon.ico',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' blob: https://www.youtube.com https://www.youtube-nocookie.com https://www.gstatic.com",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https: blob:",
              "font-src 'self' data:",
              "connect-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://www.google-analytics.com https://overbridgenet.com https://camera.mics.kaiho.mlit.go.jp https://tile.openstreetmap.org https://*.tile.openstreetmap.org ws: wss:",
              "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com",
              "media-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://camera.mics.kaiho.mlit.go.jp blob:",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'self'",
            ].join('; '),
          },
        ],
      },
    ];
  },
  
  // Allow YouTube domains and camera feeds for images and content
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'i.ytimg.com',
      },
      {
        protocol: 'https',
        hostname: 'img.youtube.com',
      },
      {
        protocol: 'https',
        hostname: 'yt3.ggpht.com',
      },
      {
        protocol: 'https',
        hostname: 'camera.mics.kaiho.mlit.go.jp',
      },
    ],
  },
};

export default nextConfig;
