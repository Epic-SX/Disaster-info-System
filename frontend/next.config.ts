import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  experimental: {
    turbo: {
      rules: {
        // Skip Turbopack for font files to avoid the resolution issue
        "*.woff2": ["file-loader"],
        "*.woff": ["file-loader"],
        "*.ttf": ["file-loader"],
      },
    },
  },
  // Alternative: disable Turbopack entirely for stable font loading
  // Remove the --turbopack flag from package.json dev script instead
};

export default nextConfig;
