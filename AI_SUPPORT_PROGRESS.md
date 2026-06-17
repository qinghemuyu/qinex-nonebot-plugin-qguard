# AI 售后中台开发进度

更新时间：2026-06-17

## 当前阶段

正在开发 `NoneBot AI 售后中台三件套`。公共底座 `nonebot_plugin_ai_core`、日志诊断 `nonebot_plugin_log_doctor`、软件知识库问答 `nonebot_plugin_group_wiki`、售后入口 `nonebot_plugin_support_bot` MVP 已落地。

## 已完成

### AI Core

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

### LogDoctor

- 新增 `nonebot_plugin_log_doctor` 插件骨架。
- 支持 `/诊断 <日志文本>`、回复消息 `/诊断`、`/诊断 最近`、`/诊断 规则列表`。
- 支持 `/报错`、`/看日志`、`/logdoctor` 入口。
- 内置规则覆盖 SQLite 数据库打不开、ModuleNotFoundError、PermissionError、FileNotFoundError、JSON/YAML/TOML 配置错误、OneBot WebSocket 连接异常、NoneBot 插件加载失败。
- 规则不命中时调用 AI Core 的结构化 JSON 诊断。
- 诊断结果写入 `diagnosis_record`，预留知识库和工单集成接口。
- 新增 LogDoctor 单元测试。

### GroupWiki

- 新增 `nonebot_plugin_group_wiki` 插件骨架。
- 支持导入仓库/项目根目录下的 `知识库` Markdown 文档。
- 支持 `/知识 导入本地`、`/知识 搜索`、`/知识 问`、`/问`、`/FAQ`、`/知识 查看`。
- 支持手动补充知识：`/知识 添加 标题 内容`。
- 支持知识反馈：`/知识 有用 K0001`、`/知识 没用 K0001`。
- 新增 SQLite 表：`wiki_article`、`wiki_article_version`、`wiki_search_index`、`wiki_feedback`。
- 检索支持中文自然问句拆词，能够命中“怎么压枪”“投屏卡顿怎么办”等 QInEX 软件问题。
- AI 问答只基于知识库片段回答，知识库不足时明确提示，不编造 QInEX 以外的信息。
- GroupWiki 群内回复标记为聊天消息，默认不会被 QGuard 自动撤回。
- 新增 GroupWiki 单元测试。

### SupportBot

- 新增 `nonebot_plugin_support_bot` 插件骨架。
- 支持 `/客服 帮助`、`/客服 状态`、`/客服 开启/关闭`、`/客服 模式 命令触发/智能监听`。
- 支持 `/求助`、`/售后`、`/不会用` 统一进入售后接待。
- 支持 `/报错` 统一接入 LogDoctor，避免 LogDoctor 与 SupportBot 双回复。
- 支持 `/人工` 和 `/工单 创建/我的/列表/查看/接单/备注/关闭/重开`。
- 新增 SQLite 表：`support_group_config`、`support_session`、`support_ticket`、`support_ticket_message`。
- 支持规则版 `SupportIntent` 意图识别：知识库问答、日志诊断、追问信息、转人工工单。
- 支持保守智能监听，默认关闭，管理员开启后才监听非命令售后关键词。
- SupportBot 群内回复标记为聊天消息，默认不会被 QGuard 自动撤回。
- 新增本地插件加载顺序回归测试，覆盖 AI Core 在后加载时的依赖解析问题。
- 新增 SupportBot 单元测试。

## 下一步

- 增强 SupportBot：AI 结构化意图识别、用户说“还是不行”自动关联上一轮会话并建单。
- 打通 LogDoctor -> GroupWiki -> SupportBot 的知识沉淀链路：结案一键生成候选知识。
- 继续完善 LogDoctor：上传文件诊断、手动添加规则、生成知识库候选、转工单。
