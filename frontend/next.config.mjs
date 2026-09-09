/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
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
