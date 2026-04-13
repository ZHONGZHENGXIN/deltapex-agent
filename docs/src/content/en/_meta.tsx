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
    title: 'Quick Start',
    theme: {
      timestamp: false,
      layout: 'full',
      navbar: true,
      toc: true,
    },
  },
  introduction: {
    title: 'Introduction',
    type: 'page',
  },
  architecture: {
    title: 'System Architecture',
    type: 'page',
  },
  'admin-guide': {
    title: 'Admin Guide',
    type: 'page',
  },
  'user-guide': {
    title: 'User Guide',
    type: 'page',
  },
  development: {
    title: 'Development Guide',
    type: 'page',
  },
  deployment: {
    title: 'Deployment Guide',
    type: 'page',
  },
  'api-reference': {
    title: 'API Reference',
    type: 'page',
  },
  troubleshooting: {
    title: 'Troubleshooting',
    type: 'page',
  },
  changelog: {
    title: (
      <span className="flex items-center leading-[1]">
        Changelog
        <TitleBadge />
      </span>
    ),
    type: 'page',
  },

} satisfies MetaRecord
