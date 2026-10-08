import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  agentRules: false,
  // Images are served by the FastAPI backend; we use plain <img> so no remotePatterns needed.
};

export default nextConfig;
