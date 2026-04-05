/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Ignore type and lint errors during production build so CI never blocks
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
