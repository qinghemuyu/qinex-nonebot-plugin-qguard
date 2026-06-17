# AI 售后中台开发进度

更新时间：2026-06-17

## 当前阶段

开始开发 `NoneBot AI 售后中台三件套`。按照设计文档顺序，第一步先实现公共底座 `nonebot_plugin_ai_core`，后续 LogDoctor、GroupWiki、SupportBot 都必须通过它调用模型。

## 已完成

- 新增 `nonebot_plugin_ai_core` 插件骨架。
- 支持 OpenAI-compatible Chat Completions 客户端，DeepSeek/OpenAI/通义兼容网关/Ollama OpenAI-compatible server 都走同一接口。
- 新增 `AICoreService.chat/classify/extract_json/summarize`。
- 新增 `get_ai_core()` 供其他插件复用。
- 新增 SQLite 表：`ai_usage_log`、`ai_cache`、`ai_rate_limit`。
- 新增按用户、群、全局的每日调用限流。
- 新增可选缓存、调用日志、敏感信息脱敏、JSON 提取。
- 新增 `/ai状态`，仅超级管理员可查看。
- 新增 `/ai测试`，用于真实调用模型检查 API Key、Base URL 和模型是否可用。
- AI Core 群内回复标记为聊天消息；是否撤回由 QGuard 的自动撤回分类配置决定，默认保留。
- 新增 AI Core 单元测试。

## 下一步

- 开发 `nonebot_plugin_log_doctor`：`/诊断`、内置规则、AI 兜底、诊断记录。
- 然后开发 `nonebot_plugin_group_wiki`：`/知识 添加`、`/知识 搜索`、`/问`。
- 最后开发 `nonebot_plugin_support_bot`：`/求助`、`/报错`、`/人工`、轻量工单。
