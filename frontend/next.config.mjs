/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";
    const simulator = process.env.SIMULATOR_INTERNAL_URL ?? "http://simulator:9000";
    return [
      { source: "/api/:path*", destination: `${backend}/:path*` },
      { source: "/simulator/:path*", destination: `${simulator}/:path*` },
    ];
  },
};

export default nextConfig;
