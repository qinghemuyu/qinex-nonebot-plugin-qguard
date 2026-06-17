# QInEX 智能问答开发进度

更新时间：2026-06-17

## 当前阶段

正在开发 QInEX 映射软件专属智能问答系统。公共底座 `nonebot_plugin_ai_core`、软件知识库 `nonebot_plugin_group_wiki`、问答入口 `nonebot_plugin_support_bot` 已落地。当前设计已取消工单、转人工、`/报错`、`/诊断` 用户入口，聚焦“按群选择知识库范围和 skills 后的知识库 RAG 问答”。

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

- 代码内部保留 `nonebot_plugin_log_doctor` 诊断服务和单元测试，方便后续开发侧排错。
- 当前 QInEX 智能问答方案不注册 `/报错`、`/诊断`、`/看日志`、`/logdoctor` 群命令。
- 用户发“打不开、没反应、报错了”这类描述时，统一按 QInEX 知识库问答和追问澄清处理。

### GroupWiki

- 新增 `nonebot_plugin_group_wiki` 插件骨架。
- 支持导入仓库/项目根目录下的 `知识库` Markdown 文档。
- 支持 `/知识 导入本地`、`/知识 搜索`、`/知识 问`、`/问`、`/FAQ`、`/知识 查看`。
- 支持 `/知识 分类`、`/知识 范围`、`/知识 技能`、`/知识 范围 全部`、`/知识 范围 分类 <分类1,分类2>`、`/知识 范围 技能 <skill_id>`，每个群可以选择自己的知识库回答范围。
- 知识分类已对齐真实 `知识库` 文件名，例如 `06_连点与压枪`、`07_投屏ScreenHub`、`08_P4单机版`。
- 新增 QInEX skills registry：`qinex_basic`、`qinex_mapping`、`qinex_recoil_click`、`qinex_screenhub`、`qinex_p4`、`qinex_troubleshooting`。
- `FAQ问答对` 作为共享检索燃料参与 RAG，但按 skill/chunk 标签过滤，不绕过群范围。
- 支持手动补充知识：`/知识 添加 标题 内容`。
- 支持知识反馈：`/知识 有用 K0001`、`/知识 没用 K0001`。
- 新增 SQLite 表：`wiki_article`、`wiki_article_version`、`wiki_search_index`、`wiki_feedback`、`wiki_group_scope_config`。
- 检索支持中文自然问句拆词，能够命中“怎么压枪”“投屏卡顿怎么办”等 QInEX 软件问题。
- AI 问答只基于知识库片段回答，知识库不足时明确提示，不编造 QInEX 以外的信息。
- AI 回答引用口径改为 `文件名#小节`，例如 `06_连点与压枪#压枪`。
- GroupWiki 群内回复标记为聊天消息，默认不会被 QGuard 自动撤回。
- 新增 GroupWiki 单元测试。

### QInEX AnswerBot

- 新增 `nonebot_plugin_support_bot` 插件骨架。
- 支持 `/客服 帮助`、`/客服 状态`、`/客服 开启/关闭`、`/客服 模式 命令触发/智能监听`。
- 支持 `/求助`、`/售后`、`/不会用` 和 `@机器人 <自然语言问题>` 统一进入知识库问答。
- 用户侧文案改为 QInEX 智能问答；内部代码名 `SupportBotService` 暂时保留兼容。
- 已取消工单、人工、日志诊断入口；`/报错` 不再作为用户命令。
- 新增 SQLite 表：`support_group_config`、`support_session`、`support_no_answer`。
- 支持规则版 `SupportIntent` 意图识别：QInEX 相关判断、skill 路由、知识库问答、低质量问题追问、非 QInEX 拒答。
- 支持保守智能监听，默认关闭，管理员开启后才监听非命令售后关键词。
- QInEX AnswerBot 按 GroupWiki 的本群知识库范围和 skills 检索回答。
- QInEX AnswerBot 群内回复标记为聊天消息，默认不会被 QGuard 自动撤回。
- 知识库答不了时会记录 `support_no_answer`，并私聊通知 `SUPPORT_BOT_ADMINS` 中的主人。
- 新增本地插件加载顺序回归测试，覆盖 AI Core 在后加载时的依赖解析问题。
- 新增 SupportBot 单元测试。

## 下一步

- 增强 GroupWiki：导入时按 FAQ 小节生成更稳定的 chunk_id，进一步提高 `文件名#小节` 引用稳定性。
- 增强 QInEX AnswerBot：用 AI Core 做结构化 skill 路由和追问生成，但仍只基于知识库回答。
- 补强知识库：给 12 篇文档补“用户常见说法”和“仍然不行时需要补充”。
