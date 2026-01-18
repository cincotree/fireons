import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  images: {
    unoptimized: true, // Required for static export
  },
  // Uncomment if deploying to GitHub Pages with repo name in path
  // basePath: '/fireons-website',
};

export default nextConfig;
