const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''
const apiBasePath = process.env.NEXT_PUBLIC_API_URL || `${basePath}/api-proxy`

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  basePath,
  trailingSlash: true,
  // REST endpoints under the routed API proxy must keep their original
  // slash form. Otherwise Next redirects POST requests before the rewrite.
  skipTrailingSlashRedirect: true,
  env: {
    NEXT_PUBLIC_API_URL: apiBasePath,
  },
  async rewrites() {
    return [{ source: '/api-proxy/:path*', destination: `${process.env.INTERNAL_API_URL || 'http://api:8000'}/:path*` }]
  },
}

module.exports = nextConfig
