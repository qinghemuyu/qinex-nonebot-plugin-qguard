# nonebot-plugin-qguard

QGuard 是一组基于 NoneBot 2 + OneBot v11 的 QQ 群管理与 QInEX 智能问答插件。仓库包含群管、知识库问答、AI Core、词云、授权登记等模块，适合长期运行在 QQ 群里的售后/社群机器人。

## 功能概览

- `nonebot_plugin_qguard`：群管主插件，提供权限、禁言、踢人、撤回、名片锁、入群审核、新人保护、广告检测、刷屏检测、自动巡检、自动清理、审计日志。
- `nonebot_plugin_ai_core`：OpenAI-compatible AI 接入层，支持 DeepSeek、OpenAI 兼容网关和 Ollama 兼容服务。
- `nonebot_plugin_group_wiki`：Markdown 知识库导入、检索、群级知识范围和 skills。
- `nonebot_plugin_support_bot`：QInEX 专属智能问答入口，支持 `/求助`、`/售后`、`/不会用` 和 @机器人自然语言提问。
- `nonebot_plugin_qfun`：群娱乐/统计能力，目前包含消息词云和每日定时发送。
- `nonebot_plugin_qlicense`：S3/P4 板子自助登记、QQ 配额和授权服务联动。
- `nonebot_plugin_log_doctor`：开发侧日志诊断底座，当前不默认暴露用户命令。

## 文档

- [部署与升级](docs/DEPLOYMENT.md)
- [配置说明](docs/CONFIGURATION.md)
- [命令索引](docs/COMMANDS.md)
- [架构说明](docs/ARCHITECTURE.md)
- [开源检查清单](docs/OPEN_SOURCE_CHECKLIST.md)
- [开发路线](PROGRESS.md)
- [AI 问答进度](AI_SUPPORT_PROGRESS.md)

## 快速安装

```bash
git clone https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard.git
cd qinex-nonebot-plugin-qguard
python3 -m pip install -e . --no-build-isolation
```

如果你的 NoneBot 项目使用 `plugin_dirs = ["src/qinex/plugins"]` 这种本地插件目录方式，可以把各插件目录复制到项目的插件目录中加载。完整服务器升级命令见 [部署与升级](docs/DEPLOYMENT.md)。

## 最小配置

复制 `.env.example` 到你的 NoneBot 项目 `.env`，至少修改这些值：

```env
QGUARD_SUPER_ADMINS=[1348984838]
QGUARD_COMMAND_PREFIX=/管

AI_CORE_PROVIDER=deepseek
AI_CORE_BASE_URL=https://api.deepseek.com
AI_CORE_API_KEY=sk-change-me
AI_CORE_MODEL=deepseek-chat

GROUP_WIKI_IMPORT_DIR=./知识库
SUPPORT_BOT_ADMINS=[1348984838]
```

`1348984838` 是示例主人 QQ，公开部署或二次开发时请改成自己的 QQ。更多环境变量见 [配置说明](docs/CONFIGURATION.md)。

## OneBot v11 连接

NoneBot 需要启用 `nonebot-adapter-onebot`，协议端通过反向 WebSocket 连接到 NoneBot，例如：

```text
ws://127.0.0.1:8080/onebot/v11/ws
```

不要把 `plugin_dirs` 里的插件目录软链接到项目外部路径。NoneBot 会按真实路径解析本地插件模块名，软链接到项目外时可能启动失败。

## 知识库

仓库内 `知识库/` 是 QInEX 映射软件的公开使用文档，可由 GroupWiki 导入后参与智能问答。知识库不包含授权算法、密钥、源码实现或绕过方式。部署时把 `知识库` 目录复制到 NoneBot 项目根目录，或用 `GROUP_WIKI_IMPORT_DIR` 指向它，然后执行：

```text
/知识 导入本地
```

许可证注意：插件源码按 MIT 开源；`知识库/` 只允许公开查阅、QInEX 使用参考和随本仓库机器人使用，不按 MIT 授权二次分发。详见 [QInEX Knowledge Base License](KNOWLEDGE_BASE_LICENSE.md)。

## 授权登记说明

`nonebot_plugin_qlicense` 只负责和你的授权服务做加密内部 API 交互，不在机器人仓库保存 S3/P4 授权私钥。P4 在线激活必须在授权服务端配置 `P4_PRIVKEY_PATH`，并确保私钥和固件内置公钥是一对。详细配置和升级顺序见 [部署与升级](docs/DEPLOYMENT.md)。

## 测试

```bash
python -m pytest
```

当前测试覆盖群管核心逻辑、插件注册中心、知识库、智能问答、词云和授权登记客户端。

## 开源注意

本仓库 `.gitignore` 已排除本地 `.env`、数据库、构建产物、压缩包、密钥文件和内部 AI 提示词设计稿。开源前请再按 [开源检查清单](docs/OPEN_SOURCE_CHECKLIST.md) 做一次确认。

## License

代码、测试和开发文档：MIT。

`知识库/`：保留版权，单独授权，详见 [KNOWLEDGE_BASE_LICENSE.md](KNOWLEDGE_BASE_LICENSE.md)。
