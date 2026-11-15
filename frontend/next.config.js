/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || "http://localhost:8080";
    return [
      {
        source: "/api/public/:path*",
        destination: `${apiBase}/api/public/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
