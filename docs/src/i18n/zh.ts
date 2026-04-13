export default {
  systemTitle: 'BAIT',
  banner: {
    title: '👋 欢迎使用 Build AI Template！',
    more: '了解详情',
  },
  pageTitle: '当前页面',
  backToTop: '返回顶部',

  search: {
    placeholder: '搜索...',
    noResults: '没有搜索结果',
    errorText: '搜索出错',
    loading: '加载中...',
  },

  badgeTitle: '开源、高效、易用 🎉',
  featureSupport: `🔥 现在支持 {{feature}}！`,
  lastUpdated: '最后更新于:',

  getStarted: '快速开始',
  liveDemo: '在线体验',

  themeSwitcher: {
    light: '浅色模式',
    dark: '深色模式',
    lightAria: '切换到浅色模式',
    darkAria: '切换到深色模式',
  },

  featureList: [
    {
      title: '全栈 AI 应用架构',
      description: '集成 Next.js 15 + FastAPI + PostgreSQL + Redis，提供完整的 AI 应用开发解决方案',
    },
    {
      title: '智能对话系统',
      description: '内置 AI Agent 框架，支持流式响应、上下文管理和多轮对话，轻松构建智能助手',
    },
    {
      title: 'OpenAI API 集成',
      description: '深度集成 OpenAI API，支持 GPT-4、函数调用和工具使用，快速实现 AI 功能',
    },
    {
      title: '用户管理系统',
      description: '完整的用户认证、权限管理和会员系统，支持邮箱验证码登录和多级权限控制',
    },
    {
      title: '现代化 UI 组件',
      description: '基于 Tailwind CSS + Shadcn UI 构建，提供美观、响应式的用户界面组件',
    },
    {
      title: '国际化支持',
      description: '内置中英文双语支持，使用 next-intl 实现完整的国际化解决方案',
    },
    {
      title: '数据库 ORM',
      description: '使用 SQLModel + Alembic 进行数据库管理，支持类型安全的数据操作和版本迁移',
    },
    {
      title: 'Docker 部署',
      description: '提供完整的 Docker 配置，支持一键部署到生产环境和测试环境',
    },
    {
      title: '开发者友好',
      description: '详细的中文注释、完善的文档和最佳实践，让开发者快速上手 AI 应用开发',
    },
  ],
  featuresDesc: '快速构建生产级 AI 应用，从原型到部署一站式解决',
  faqs: [
    {
      question: 'Build AI Template 支持哪些 AI 模型？',
      answer: '支持所有主流 AI 服务商，包括 OpenAI (GPT-5)、Anthropic (Claude)、DeepSeek、阿里通义千问 (Qwen)、百度文心一言等。框架设计灵活，可以轻松切换和扩展不同的 AI 模型。',
    },
    {
      question: '如何快速开始使用这个模板？',
      answer: '克隆项目后，按照文档配置环境变量，运行 Docker Compose 即可启动完整的开发环境。详细步骤请参考快速开始指南。',
    },
    {
      question: '这个模板适合构建什么类型的 AI 应用？',
      answer: '适合构建各种 AI 对话应用，如智能客服、AI 助手、知识问答系统、代码生成工具等。模板提供了完整的基础架构。',
    },
    {
      question: '如何自定义 AI Agent 的行为？',
      answer: '可以通过修改 Agent 配置、自定义 prompt 模板、添加工具函数等方式来定制 AI 的行为和能力。',
    },
    {
      question: '模板是否支持多租户和权限管理？',
      answer: '是的，内置了完整的用户管理和权限系统，支持多级权限控制、会员管理和使用限制等功能。',
    },
    {
      question: '如何获得技术支持？',
      answer: '可以通过 GitHub Issues 提问，或者查看详细的文档和示例代码。我们会及时回复和更新。',
    },
    {
      question: '🤖 这个项目的特色是什么？',
      answer: '专注于 AI 应用开发！🚀 提供从前端到后端的完整解决方案，让你专注于 AI 逻辑而不是基础架构。',
    },
  ],

}
