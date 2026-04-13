import type { MetaRecord } from 'nextra'
import { TitleBadge } from '@/components/TitleBadge'


export default {
  index: {
    type: 'page',
    display: 'hidden',
    theme: {
      timestamp: false,
      layout: 'full',
      toc: false,
    },
  },
  'quick-start': {
    type: 'page',
    title: '快速开始',
    theme: {
      timestamp: false,
      layout: 'full',
      navbar: true,
      toc: true,
    },
  },
  introduction: {
    title: '项目介绍',
    type: 'page',
  },
  architecture: {
    title: '系统架构',
    type: 'page',
  },
  'admin-guide': {
    title: '管理员指南',
    type: 'page',
  },
  'user-guide': {
    title: '用户指南',
    type: 'page',
  },
  development: {
    title: '开发指南',
    type: 'page',
  },
  deployment: {
    title: '部署指南',
    type: 'page',
  },
  'api-reference': {
    title: 'API 参考',
    type: 'page',
  },
  troubleshooting: {
    title: '故障排除',
    type: 'page',
  },
  changelog: {
    title: (
      <span className="flex items-center leading-[1]">
        更新日志
        <TitleBadge />
      </span>
    ),
    type: 'page',
  },

} satisfies MetaRecord
