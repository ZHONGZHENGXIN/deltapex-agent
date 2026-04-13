import createWithNextra from 'nextra'

const withNextra = createWithNextra({
  defaultShowCopyCode: true,
  unstable_shouldAddLocaleToLinks: true,
})

/**
 * @type {import("next").NextConfig}
 */
export default withNextra({
  // 设置输出文件追踪根目录为当前项目目录，避免与其他 Next.js 项目冲突
  output: 'standalone',
  outputFileTracingRoot: __dirname,
  // 设置服务器默认端口为 4000
  serverRuntimeConfig: {
    port: 4000,
  },
  images: {
    unoptimized: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  reactStrictMode: true,
  cleanDistDir: true,
  i18n: {
    locales: ['zh', 'en'],
    defaultLocale: 'zh',
  },
  sassOptions: {
    silenceDeprecations: ['legacy-js-api'],
  },
})
