# 开源检查清单

发布到 GitHub 前建议逐项确认。

## 文件检查

- `.env` 没有提交。
- `data/` 没有提交。
- `*.db`、`*.sqlite`、`*.sqlite3` 没有提交。
- `*.pem`、`*.key`、`*.crt` 没有提交。
- `*.zip`、`*.tar.gz` 没有提交。
- `QGuard_OneBot_v11_详细开发设计_AI提示词.md` 没有提交。
- `NoneBot_AI_*.md` 没有提交。
- 授权服务私钥、S3/P4 授权算法、密钥、生成规则没有提交。
- 真实 AI API Key、OneBot access token、授权服务 HMAC secret 没有提交。

仓库 `.gitignore` 已覆盖上述常见文件，但开源前仍建议执行：

```bash
git status --short
git ls-files
```

## 敏感字符串扫描

```bash
rg -n "sk-|api[_-]?key|secret|token|password|PRIVATE|私钥|密钥|授权算法|破解|绕过" .
```

允许出现的情况：

- `.env.example` 中的占位符。
- 文档中提醒用户不要泄露密钥。
- 代码中配置字段名或脱敏规则。
- 单元测试中的假数据。

不允许出现的情况：

- 真实 API Key。
- 真实授权服务 secret。
- 私钥文件内容。
- 真实数据库内容。
- 内部 AI 提示词设计稿。

## 开源仓库建议结构

```text
README.md
LICENSE
.env.example
docs/
nonebot_plugin_qguard/
nonebot_plugin_ai_core/
nonebot_plugin_group_wiki/
nonebot_plugin_support_bot/
nonebot_plugin_qfun/
nonebot_plugin_qlicense/
nonebot_plugin_log_doctor/
tests/
知识库/
```

## 发布前验证

```bash
python -m pytest
git diff --check
```

如果要从 Windows 打包上传服务器测试：

```powershell
cd F:\code\nonebot\qinex
git archive --format=zip --output F:\code\nonebot\qinex-update.zip HEAD
```

压缩包不应提交到 GitHub。不要用 `Compress-Archive -Path F:\code\nonebot\qinex\*` 直接压整个工作目录，那样会把 Git 忽略但本地存在的提示词、`.env`、数据库、临时文件一起打进去。

## 公开说明边界

本仓库可以公开：

- QQ 群管理逻辑。
- AI Core 调用框架。
- QInEX 公开使用知识库。
- S3/P4 自助登记客户端逻辑。
- 授权服务内部 API 的调用方式和安全约束。

本仓库不应公开：

- 授权服务私钥。
- S3/P4 授权生成算法的私密部分。
- 真实用户数据库。
- 真实授权绑定表。
- 真实订单、付款、手机号、完整授权码。
- 内部 AI 提示词设计稿。
