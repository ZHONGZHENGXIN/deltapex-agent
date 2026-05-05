# tracoach 上线前人工闭环清单

本清单用于代码修复完成后的上线前人工验收。不要在本文档、日志、截图或 commit 中粘贴真实 API key、数据库 URL、用户邮箱明文或 provider token。

## 当前结论

- P0/P1/P2 代码修复项已完成并有自动化测试记录。
- 仍未闭环的上线阻塞项主要是人工操作和部署验证。
- 在 P0-1 外部 provider key 轮换、P1-1 one-api 生产启用/failover 验证完成前，不建议开放真实学员。

## 阻塞项

| 编号 | 项目 | 当前状态 | 上线要求 | 回填 |
|---|---|---|---|---|
| B1 | 外部 provider key 轮换 | 待人工执行 | FastGPT/OpenAI/Coze/Dify 等已暴露或可能暴露的 key 重新生成、更新 Zeabur 配置、撤销旧 key | 执行人/日期/provider |
| B2 | one-api 生产启用 | 待部署配置 | `LLM_GATEWAY_ENABLED=true`，配置 one-api base URL、token、模型别名 | 执行人/日期/截图 |
| B3 | one-api failover 验证 | 待人工验证 | 主 channel/key 失效时，聊天能切换到备用 channel，或返回明确降级提示 | 测试时间/结果 |
| B4 | 生产备份文件生成 | 待人工确认 | Zeabur PostgreSQL 至少成功生成一次 dump，并校验 sha256 | 备份文件名/校验结果 |
| B5 | staging 恢复演练 | 可灰度后补，公开发布前建议完成 | 按 `ops/backup-recovery.md` 恢复到 staging，并回填 `ops/recovery-rehearsal-log.md` | RTO/问题记录 |
| B6 | 法务与合规口径确认 | 待 Alex/法务确认 | 学员协议、隐私政策、投资建议免责声明、客服/紧急支持口径确认 | 确认人/日期 |
| B7 | 监控面板归档 | 待部署后截图 | Zeabur 管理后台 `/admin` 监控区截图或外部 dashboard 链接归档 | 链接/截图路径 |

## Zeabur 环境变量核查

在 `deltapex-api` 服务中核查以下变量。不要把真实值写入 git。

### 安全与限流

```env
CHAT_RATE_LIMIT_ENABLED=true
CHAT_RATE_LIMIT_MAX_REQUESTS=30
CHAT_RATE_LIMIT_WINDOW_SECONDS=1
CONTENT_MODERATION_ENABLED=true
COMPLIANCE_SUPPORT_CONTACT=你的客服或支持入口
```

### one-api 网关

如果继续临时直连 FastGPT：

```env
LLM_GATEWAY_ENABLED=false
```

准备接真实学员或生产发布前，应切到 one-api：

```env
LLM_GATEWAY_ENABLED=true
LLM_GATEWAY_BASE_URL=https://你的-one-api-地址/v1
LLM_GATEWAY_API_KEY=one-api 生成的 token
LLM_GATEWAY_MODEL_NAME=one-api 模型或渠道别名
```

### 监控

```env
MONITORING_WINDOW_SIZE=5000
MONITORING_P99_ALERT_MS=5000
MONITORING_ERROR_RATE_ALERT_THRESHOLD=0.05
MONITORING_LLM_FAILURE_RATE_ALERT_THRESHOLD=0.10
MONITORING_TOKEN_ALERT_DAILY_THRESHOLD=100000
QUALITY_SAMPLE_DAILY_LIMIT=50
MONITORING_EXTERNAL_DASHBOARD_URL=
ONE_API_DASHBOARD_URL=
CLAUDE_METER_DASHBOARD_URL=
```

## 部署后 smoke test

1. Zeabur 重新部署 `deltapex-api` 和 `deltapex-web`。
2. 在 `deltapex-api` 命令行执行：

```sh
python -m alembic current
```

确认当前版本不低于最近一次 migration head。

3. 管理员登录后台，打开仪表盘。
4. 普通学员登录，新建聊天并发送一条正常消息。
5. 用浏览器 Network 检查：
   - `/api/v1/chat/agents/active` 不返回 `api_key`。
   - `/api/v1/chat/{chat_id}` 的 `agent` 不返回 `api_key`。
   - `/api/v1/chat/message` 请求体只有 `chat_id` 和 `content`。
6. 访问管理后台监控区，确认能看到：
   - P99 latency。
   - API error rate。
   - LLM channel failure rate。
   - Token outlier alert。
   - AI output sample queue。

## 灰度规则

灰度只开放 5-10 个内部信任学员，至少观察 2 周。

观察项：

- P99 延迟是否持续高于阈值。
- API error rate 是否高于 5%。
- LLM channel failure rate 是否高于 10%。
- 是否出现单学员异常 token 消耗。
- 内容审核是否误伤正常问题，或漏掉明显高风险输出。
- 账号删除、聊天删除、跨用户访问防护是否正常。

## 回填表

| 日期 | 执行人 | 环境 | 项目 | 结果 | 证据链接或截图路径 | 后续问题 |
|---|---|---|---|---|---|---|
|  |  | production/staging | provider key 轮换 |  |  |  |
|  |  | production/staging | one-api 启用 |  |  |  |
|  |  | staging | one-api failover |  |  |  |
|  |  | production | 备份文件生成 |  |  |  |
|  |  | staging | 恢复演练 |  |  |  |
|  |  | production | 法务/合规确认 |  |  |  |
|  |  | production | 监控面板归档 |  |  |  |
