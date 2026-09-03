// next.config.js improvements
module.exports = {
  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
  },
  // Bundle optimization
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // Analytics
  analyticsId: process.env.VERCEL_ANALYTICS_ID,
}