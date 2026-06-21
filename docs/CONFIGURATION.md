# 配置说明

配置写在 NoneBot 项目的 `.env` 中。仓库提供 `.env.example`，生产环境不要提交真实 `.env`。

## 基础服务

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DRIVER` | `~fastapi+~websockets` | NoneBot 驱动 |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `8080` | 监听端口 |
| `ONEBOT_V11_ACCESS_TOKEN` | `change-me-to-a-long-random-token` | OneBot v11 连接 token |

## QGuard 群管

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QGUARD_DB_URL` | `sqlite+aiosqlite:///./data/qguard.db` | 群管数据库 |
| `QGUARD_SUPER_ADMINS` | `[1348984838]` | 机器人主人 QQ 列表 |
| `QGUARD_DEFAULT_ENABLE` | `true` | 新群默认启用 |
| `QGUARD_DEFAULT_MUTE_SECONDS` | `600` | 默认禁言秒数 |
| `QGUARD_MESSAGE_CACHE_DAYS` | `7` | 消息缓存保留天数 |
| `QGUARD_CARD_LOCK_PATROL_INTERVAL_SECONDS` | `600` | 名片锁巡检间隔 |
| `QGUARD_AUTO_PATROL_INTERVAL_SECONDS` | `1800` | 综合自动巡检默认间隔 |
| `QGUARD_ENABLE_AUTO_MODERATION` | `true` | 自动审核总开关 |
| `QGUARD_ENABLE_MESSAGE_CACHE` | `true` | 消息缓存总开关 |
| `QGUARD_COMMAND_PREFIX` | `/管` | 群管命令前缀 |

## AI Core

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `AI_CORE_PROVIDER` | `deepseek` | 提供商标识 |
| `AI_CORE_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible base URL |
| `AI_CORE_API_KEY` | 空 | AI API Key |
| `AI_CORE_MODEL` | `deepseek-chat` | 模型名 |
| `AI_CORE_TIMEOUT_SECONDS` | `45` | 请求超时 |
| `AI_CORE_MAX_TOKENS` | `2048` | 默认最大输出 token |
| `AI_CORE_TEMPERATURE` | `0.2` | 默认温度 |
| `AI_CORE_ENABLE_CACHE` | `true` | 是否启用缓存 |
| `AI_CORE_CACHE_TTL_SECONDS` | `86400` | 缓存 TTL |
| `AI_CORE_DAILY_LIMIT_PER_USER` | `30` | 单用户每日限制 |
| `AI_CORE_DAILY_LIMIT_PER_GROUP` | `300` | 单群每日限制 |
| `AI_CORE_GLOBAL_DAILY_LIMIT` | `5000` | 全局每日限制 |
| `AI_CORE_ENABLE_JSON_REPAIR` | `true` | JSON 结果自动修复 |
| `AI_CORE_ENABLE_CONTENT_MASK` | `true` | 敏感信息脱敏 |
| `AI_CORE_LOG_PROMPT` | `false` | 是否记录 prompt 明文 |
| `AI_CORE_LOG_RESPONSE` | `false` | 是否记录回复明文 |
| `AI_CORE_DB_URL` | `sqlite+aiosqlite:///./data/ai_core.db` | AI Core 数据库 |
| `AI_CORE_SUPER_ADMINS` | `[1348984838]` | AI 管理员 |

建议生产环境保持 `AI_CORE_LOG_PROMPT=false` 和 `AI_CORE_LOG_RESPONSE=false`。

## GroupWiki 知识库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `GROUP_WIKI_DB_URL` | `sqlite+aiosqlite:///./data/group_wiki.db` | 知识库数据库 |
| `GROUP_WIKI_ENABLE_AI` | `true` | 是否允许 AI 问答 |
| `GROUP_WIKI_DEFAULT_SCOPE` | `global` | 默认知识范围 |
| `GROUP_WIKI_IMPORT_DIR` | `./知识库` | 本地 Markdown 知识库目录 |
| `GROUP_WIKI_MAX_ARTICLE_LENGTH` | `20000` | 单篇最大导入字符数 |
| `GROUP_WIKI_CHUNK_SIZE` | `800` | 切片大小 |
| `GROUP_WIKI_CHUNK_OVERLAP` | `100` | 切片重叠 |
| `GROUP_WIKI_MAX_REPLY_CHARS` | `1200` | 最大回复长度 |
| `GROUP_WIKI_SOFTWARE_NAME` | `QInEX` | 软件名 |

## QInEX AnswerBot

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SUPPORT_BOT_DB_URL` | `sqlite+aiosqlite:///./data/support_bot.db` | 问答数据库 |
| `SUPPORT_BOT_ENABLED` | `true` | 默认启用 |
| `SUPPORT_BOT_TRIGGER_MODE` | `command` | 默认命令触发 |
| `SUPPORT_BOT_ENABLE_SMART_LISTEN` | `false` | 是否默认智能监听 |
| `SUPPORT_BOT_MIN_INTENT_CONFIDENCE` | `0.78` | 意图置信度阈值 |
| `SUPPORT_BOT_SESSION_TTL_SECONDS` | `1800` | 会话保留时间 |
| `SUPPORT_BOT_CONVERSATION_TTL_SECONDS` | `180` | 连续对话上下文时间 |
| `SUPPORT_BOT_MAX_REPLY_LENGTH` | `1200` | 最大回复长度 |
| `SUPPORT_BOT_SOFTWARE_NAME` | `QInEX` | 软件名 |
| `SUPPORT_BOT_ADMINS` | `[1348984838]` | 未命中/未解决通知对象 |
| `SUPPORT_BOT_UNRESOLVED_ESCALATION_TURNS` | `10` | 同一问题多轮未解决后私聊给主人 |
| `SUPPORT_BOT_ALLOW_CASUAL_CHAT` | `true` | @机器人或命令入口允许轻量闲聊 |
| `SUPPORT_BOT_CASUAL_CHAT_MAX_TOKENS` | `260` | 闲聊回复最大 token |
| `SUPPORT_BOT_HARASSMENT_ENABLED` | `true` | 是否启用骚扰惩罚联动 |
| `SUPPORT_BOT_HARASSMENT_WINDOW_SECONDS` | `300` | 骚扰统计窗口 |
| `SUPPORT_BOT_HARASSMENT_WARN_THRESHOLD` | `3` | 警告阈值 |
| `SUPPORT_BOT_HARASSMENT_SCORE_THRESHOLD` | `5` | 接入群管积分阈值 |
| `SUPPORT_BOT_HARASSMENT_SCORE_COOLDOWN_SECONDS` | `60` | 加分冷却 |
| `SUPPORT_BOT_HARASSMENT_SCORE_DELTA` | `1` | 单次加分 |
| `SUPPORT_BOT_HARASSMENT_MAX_SCORE_DELTA` | `3` | 单窗口最高加分 |

## QFun 词云

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QFUN_DB_URL` | `sqlite+aiosqlite:///./data/qfun.db` | 词云数据库 |
| `QFUN_DEFAULT_ENABLED` | `true` | 默认启用 |
| `QFUN_WORDCLOUD_DEFAULT_TIME` | `21:30` | 默认每日发送时间 |
| `QFUN_WORDCLOUD_DEFAULT_PERIOD` | `今日` | 默认统计范围 |
| `QFUN_WORDCLOUD_TOP_LIMIT` | `20` | 词云词条数量 |
| `QFUN_WORDCLOUD_MESSAGE_LIMIT` | `5000` | 最大统计消息数 |
| `QFUN_SUPER_ADMINS` | `[1348984838]` | 词云管理员 |

## QLicense 授权登记

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QLICENSE_API_BASE_URL` | `http://127.0.0.1:5000` | 授权服务地址 |
| `QLICENSE_BOT_ID` | `qinex-nonebot` | 内部 API bot id |
| `QLICENSE_API_SECRET` | 空 | 内部 API HMAC 密钥 |
| `QLICENSE_TIMEOUT_SECONDS` | `8` | 请求超时 |
| `QLICENSE_REQUIRE_SECURE_TRANSPORT` | `true` | 非 localhost 地址强制 HTTPS |
| `QLICENSE_SUPER_ADMINS` | `[1348984838]` | 授权管理命令管理员 |

机器人与授权服务的共享密钥关系：

```text
QLICENSE_API_SECRET == LICENSE_BOT_API_SECRET
QLICENSE_BOT_ID == LICENSE_BOT_ID
```

授权服务端的 P4 私钥只放授权服务，不放机器人仓库。

## SQLite 数据库

默认所有数据库都放在项目 `data/` 目录。`data/` 已被 `.gitignore` 排除，开源时不会提交。

升级前建议备份：

```bash
cd /home/NoneBot/qinex
tar czf /home/NoneBot/qinex-data-backup-$(date +%F-%H%M%S).tar.gz data
```
