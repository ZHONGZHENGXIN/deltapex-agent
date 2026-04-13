# Build AI Template - Cursor Rules 目录

这是 Build AI Template 项目的 Cursor Rules 集合，用于帮助 AI 助手更好地理解项目结构和编码规范。

## 📁 规则文件说明

### 🏗️ 项目结构规则（始终应用）

- **[project-structure.mdc](project-structure.mdc)** - 项目整体结构和目录说明
- **[quick-reference.mdc](quick-reference.mdc)** - 快速参考指南，包含常用命令和配置
- **[quick-comments-guide.mdc](quick-comments-guide.mdc)** - 代码注释规范和模板

### 💻 开发规范规则（按需调用）

#### 前端开发

- **[frontend-rules.mdc](frontend-rules.mdc)** - 前端开发规范
  - React/Next.js 最佳实践
  - TypeScript 类型定义
  - 组件开发模板
  - 数据缓存和性能优化

- **[i18n-styling.mdc](i18n-styling.mdc)** - 样式和国际化规范
  - Tailwind CSS 使用
  - Shadcn UI 组件
  - 国际化配置
  - 主题系统

#### 后端开发

- **[backend-rules.mdc](backend-rules.mdc)** - 后端开发规范
  - FastAPI/Python 最佳实践
  - API 路由开发
  - 异常处理和安全
  - 导入规范和代码组织

- **[database-models.mdc](database-models.mdc)** - 数据库模型规范
  - SQLModel 模型定义
  - Alembic 迁移管理
  - CRUD 操作模板
  - 查询优化技巧

- **[api-route-language-rules.mdc](api-route-language-rules.mdc)** - API 路由语言规范
  - 国际化依赖注入
  - 错误消息国际化
  - 路由开发检查清单

#### AI 和智能功能

- **[ai-agent-development.mdc](ai-agent-development.mdc)** - AI 开发规范
  - OpenAI API 集成
  - Agent 系统架构
  - 流式响应处理
  - Token 使用量统计

### 🔧 工程化规则（按需调用）

#### 测试和质量保证

- **[testing-rules.mdc](testing-rules.mdc)** - 测试开发规范
  - 单元测试和集成测试
  - E2E 测试最佳实践
  - 测试数据管理
  - CI/CD 测试集成

#### 部署和运维

- **[deployment-devops.mdc](deployment-devops.mdc)** - 部署和运维规范
  - Docker 容器化
  - CI/CD 流水线
  - 监控和日志
  - 备份和恢复

#### 安全开发

- **[security-rules.mdc](security-rules.mdc)** - 安全开发规范
  - 认证和授权
  - 输入验证和防护
  - 数据保护和加密
  - 安全监控和审计

#### 文档规范

- **[markdown-rules.mdc](markdown-rules.mdc)** - Markdown 编写规范
  - 文档格式标准
  - 代码示例规范
  - 自动化检查工具

## 🚀 使用方法

### 自动应用的规则

以下规则会自动应用到所有对话中：

- `project-structure.mdc` - 项目结构和技术栈
- `quick-reference.mdc` - 快速参考指南
- `quick-comments-guide.mdc` - 代码注释规范

### 手动调用规则

当需要特定领域的帮助时，AI 助手会自动调用相应的规则，或者您可以明确要求使用特定规则：

#### 前端开发相关

```bash
# 前端组件开发
使用 frontend-rules 规则

# 样式和国际化
使用 i18n-styling 规则
```

#### 后端开发相关

```bash
# 后端 API 开发
使用 backend-rules 规则

# 数据库模型设计
使用 database-models 规则

# API 路由国际化
使用 api-route-language-rules 规则
```

#### AI 功能开发

```bash
# AI Agent 开发
使用 ai-agent-development 规则
```

#### 工程化相关

```bash
# 测试开发
使用 testing-rules 规则

# 部署运维
使用 deployment-devops 规则

# 安全开发
使用 security-rules 规则

# 文档编写
使用 markdown-rules 规则
```

## 📝 规则维护

### 添加新规则

1. 在 `.cursor/rules/` 目录创建新的 `.mdc` 文件
2. 添加合适的 frontmatter 元数据：

   ```yaml
   ---
   description: 规则描述（用于 AI 识别和调用）
   alwaysApply: true/false # 是否自动应用
   ---
   ```

3. 编写规则内容，可以使用 `[文件名](mdc:路径)` 引用项目文件

### 更新现有规则

直接编辑对应的 `.mdc` 文件，规则会立即生效。

### 规则编写建议

1. **保持专注** - 每个规则文件聚焦一个特定领域
2. **提供示例** - 包含代码示例和模板
3. **链接文件** - 使用 `mdc:` 链接引用实际项目文件
4. **中文注释** - 遵循项目规范，使用中文注释
5. **定期更新** - 随项目发展更新规则内容

## 🔧 技术栈概览

### 前端技术栈

- **框架**: Next.js 15.3 + React 19
- **语言**: TypeScript 5.x
- **样式**: Tailwind CSS + Shadcn UI
- **国际化**: next-intl
- **状态管理**: React Hooks + Context API
- **测试**: Jest + React Testing Library + Playwright

### 后端技术栈

- **框架**: FastAPI + Python 3.12
- **数据库**: PostgreSQL 15+ + Redis 7+
- **ORM**: SQLModel + Alembic
- **认证**: JWT + bcrypt
- **测试**: pytest + pytest-asyncio
- **包管理**: uv

### AI 技术栈

- **LLM**: OpenAI API (GPT-4o-mini)
- **Agent**: 自定义 Agent 框架
- **响应**: 流式响应 (SSE)
- **功能**: Token 统计、上下文管理

### 部署和运维

- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **反向代理**: Nginx
- **监控**: 日志文件 + 健康检查
- **安全**: SSL/TLS + 入侵检测

## 📌 重要链接

- [需求文档列表](mdc:docs/*.md)
- [前端入口](mdc:web/app/[locale]/page.tsx)
- [后端入口](mdc:api/app/main.py)
- [数据模型](mdc:api/app/models/)
- [API 路由](mdc:api/app/routers/v1/)

## ⚠️ 开发注意事项

### 代码质量要求

1. **详细注释** - 所有代码必须包含详细的中文注释，说明功能、参数、返回值和业务逻辑
2. **类型安全** - 前后端都要保证类型安全，使用 TypeScript 和 Python 类型提示
3. **错误处理** - 实现完善的错误处理机制，提供用户友好的错误提示
4. **性能优化** - 注意数据库查询优化、缓存使用和前端性能
5. **安全规范** - 遵循安全最佳实践，防范常见安全漏洞

### 开发流程规范

1. **后端优先** - 先实现数据模型和 API 接口，再开发前端功能
2. **测试驱动** - 编写单元测试和集成测试，确保代码质量
3. **国际化支持** - 所有用户界面文本都要支持中英文
4. **文档同步** - 代码变更时同步更新相关文档和注释
5. **安全审查** - 涉及用户数据和权限的功能要进行安全审查

### 部署和运维

1. **环境隔离** - 开发、测试、生产环境严格隔离
2. **监控告警** - 配置完善的监控和告警机制
3. **备份策略** - 定期备份数据库和重要配置文件
4. **安全更新** - 及时更新依赖包和系统补丁
5. **日志管理** - 合理配置日志级别和轮转策略

## 📈 规则更新记录

### 最新更新 (2024-12)

- ✅ 新增 `testing-rules.mdc` - 测试开发规范
- ✅ 新增 `deployment-devops.mdc` - 部署和运维规范
- ✅ 新增 `security-rules.mdc` - 安全开发规范
- ✅ 更新 `ai-agent-development.mdc` - 完善 AI 开发流程
- ✅ 更新 `frontend-rules.mdc` - 添加数据缓存和性能优化
- ✅ 更新 `backend-rules.mdc` - 完善导入规范和错误处理

### 规则覆盖范围

- **开发规范**: 前端、后端、AI、数据库 ✅
- **工程化**: 测试、部署、安全、文档 ✅
- **最佳实践**: 性能优化、错误处理、国际化 ✅
- **项目管理**: 代码注释、版本控制、团队协作 ✅

---

_这些规则会帮助 Cursor AI 助手更好地理解项目结构，提供更准确的代码建议和解决方案。规则会随着项目发展持续更新和完善。_
