/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api-proxy',
  },
  async rewrites() {
    return [{ source: '/api-proxy/:path*', destination: `${process.env.INTERNAL_API_URL || 'http://api:8000'}/:path*` }]
  },
}

module.exports = nextConfig
