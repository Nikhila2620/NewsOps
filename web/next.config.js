/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // required for Docker Dockerfile
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.resolve = config.resolve || {}
      config.resolve.alias = {
        ...config.resolve.alias,
        'msw/browser': false,
      }
    }
    return config
  },
}

module.exports = nextConfig
