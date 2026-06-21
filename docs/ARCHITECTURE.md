# 架构说明

本仓库是一组面向 NoneBot 2 + OneBot v11 的 QQ 机器人插件。核心目标是让 QQ 群长期运行时具备群管、QInEX 智能问答、知识库检索、词云统计和授权登记能力。

## 模块划分

```text
OneBot v11
  ↓
NoneBot 2
  ↓
本仓库插件组
  ├─ nonebot_plugin_qguard       群管核心、权限、帮助中心、自动撤回、自动清理
  ├─ nonebot_plugin_ai_core      OpenAI-compatible AI 调用层
  ├─ nonebot_plugin_group_wiki   Markdown 知识库导入、检索、群范围、skills
  ├─ nonebot_plugin_support_bot  QInEX 智能问答、人设、连续对话、缺口看板
  ├─ nonebot_plugin_qfun         词云和群娱乐统计
  ├─ nonebot_plugin_qlicense     S3/P4 授权登记客户端
  └─ nonebot_plugin_log_doctor   开发侧日志诊断底座
```

## 插件协作

- `qguard` 提供统一的权限、命令帮助、消息撤回分类、用户积分和群管处罚能力。
- 其他插件通过各自的 `qguard_registry.py` 向 `qguard` 注册命令、配置项和权限说明，因此 `/管 帮助`、`/管 插件` 能自动看到新增插件能力。
- `support_bot` 依赖 `group_wiki` 做知识库检索，依赖 `ai_core` 调用模型，回答不了时记录缺口并可私信主人。
- `support_bot` 的 AI 聊天回复按 `chat_reply` 分类，不应被群管默认当作指令回执撤回。
- `support_bot` 被 @ 或命令触发时允许轻量闲聊；QInEX 软件问题仍然走知识库，普通闲聊不写入未命中缺口，也不按“非 QInEX 问题”累计骚扰分。
- `qlicense` 只保存 QQ 到设备登记关系和配额状态，真正的 S3/P4 授权签发由外部授权服务完成。

## 智能问答流程

```text
用户 @机器人 或使用 /客服、/求助
  ↓
support_bot 判断是否为 QInEX 软件问题、普通闲聊或恶意骚扰
  ↓
普通闲聊：ai_core 短回复，不进入知识库缺口
  ↓
group_wiki 根据本群启用的 skills / 知识范围检索
  ↓
低置信度时优先追问；高置信度时组织答案
  ↓
ai_core 调用 DeepSeek / OpenAI-compatible 模型
  ↓
support_bot 输出自然语言答案，记录命中、未命中、未解决和缺口
  ↓
反复无法解决时汇总私信给主人
```

知识库只包含公开使用说明和排障经验，不包含授权算法、密钥、源码实现细节或绕过方式。

## 授权登记边界

`nonebot_plugin_qlicense` 是机器人侧客户端，负责：

- 校验 QQ 配额。
- 提醒用户 MAC 必须从板子专属配置页面复制。
- 向授权服务发起带签名的内部 API 请求。
- 将 S3/P4 登记结果反馈给用户。

授权服务负责：

- 维护真实授权数据库。
- 验证机器人请求签名。
- 写入可被 `/api/license` 查询到的授权记录。
- S3/P4 授权签发、P4 私钥和固件公钥配套。

本仓库不提交授权服务源码、授权私钥、真实授权数据库、真实 HMAC secret。

## 数据与持久化

插件运行时数据默认由 NoneBot 项目的数据目录承载。常见数据包括：

- 群配置、权限、积分、处罚、自动清理记录。
- 消息缓存、撤回记录、审计日志。
- 知识库索引、问答缺口、连续对话摘要。
- 词云统计。
- QQ 与 S3/P4 设备登记信息。

这些运行时数据不应提交到 GitHub。

## 部署方式

推荐在服务器保留一份源码目录：

```text
/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard
```

再把插件目录复制到 NoneBot 项目的本地插件目录：

```text
/home/NoneBot/qinex/src/qinex/plugins
```

不要使用指向项目外部的软链接加载插件，NoneBot 会解析真实路径，可能导致本地插件模块名不在项目路径下而启动失败。
