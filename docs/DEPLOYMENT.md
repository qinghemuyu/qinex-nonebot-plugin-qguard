# 部署与升级

本文以当前生产目录为例：

- 插件源码目录：`/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard`
- NoneBot 项目目录：`/home/NoneBot/qinex`
- NoneBot 插件目录：`/home/NoneBot/qinex/src/qinex/plugins`
- 知识库目录：`/home/NoneBot/qinex/知识库`

如果你的服务器目录不同，把命令里的路径替换成自己的即可。

## 1. 首次部署

```bash
cd /home/NoneBot
mkdir -p /home/NoneBot/plugins-src
git clone https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard.git \
  /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard

cd /home/NoneBot/qinex
source .venv/bin/activate
python3 -m pip install -U pip setuptools wheel
python3 -m pip install -e /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard --no-build-isolation
```

如果你采用本地插件目录加载方式，继续复制插件目录：

```bash
cd /home/NoneBot/qinex

for d in \
  nonebot_plugin_qguard \
  nonebot_plugin_ai_core \
  nonebot_plugin_log_doctor \
  nonebot_plugin_group_wiki \
  nonebot_plugin_support_bot \
  nonebot_plugin_qfun \
  nonebot_plugin_qlicense
do
  rm -rf "/home/NoneBot/qinex/src/qinex/plugins/$d"
  cp -a "/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/$d" \
    "/home/NoneBot/qinex/src/qinex/plugins/$d"
done

rm -rf /home/NoneBot/qinex/知识库
cp -a /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/知识库 /home/NoneBot/qinex/知识库
```

确保 NoneBot 项目 `pyproject.toml` 中包含：

```toml
[tool.nonebot]
plugin_dirs = ["src/qinex/plugins"]
```

不要把插件目录软链接到项目外部路径，NoneBot 解析本地插件时会使用真实路径，可能导致启动失败。

## 2. 常规升级：git pull

```bash
cd /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard
git pull --ff-only

cd /home/NoneBot/qinex

for d in \
  nonebot_plugin_qguard \
  nonebot_plugin_ai_core \
  nonebot_plugin_log_doctor \
  nonebot_plugin_group_wiki \
  nonebot_plugin_support_bot \
  nonebot_plugin_qfun \
  nonebot_plugin_qlicense
do
  rm -rf "/home/NoneBot/qinex/src/qinex/plugins/$d"
  cp -a "/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/$d" \
    "/home/NoneBot/qinex/src/qinex/plugins/$d"
done

rm -rf /home/NoneBot/qinex/知识库
cp -a /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/知识库 /home/NoneBot/qinex/知识库
```

然后重启 NoneBot。

## 3. GitHub TLS 异常时：服务器直接下载 zip

如果 `git pull` 报 TLS 错误，可以尝试 zip 下载：

```bash
cd /home/NoneBot

rm -rf /tmp/qguard_update /tmp/qguard-main.zip
mkdir -p /tmp/qguard_update

curl -L -k --retry 5 --connect-timeout 30 \
  -o /tmp/qguard-main.zip \
  https://codeload.github.com/qinghemuyu/qinex-nonebot-plugin-qguard/zip/refs/heads/main

python3 -m zipfile -e /tmp/qguard-main.zip /tmp/qguard_update

rm -rf /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard
mv /tmp/qguard_update/qinex-nonebot-plugin-qguard-main \
  /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard

cd /home/NoneBot/qinex

for d in \
  nonebot_plugin_qguard \
  nonebot_plugin_ai_core \
  nonebot_plugin_log_doctor \
  nonebot_plugin_group_wiki \
  nonebot_plugin_support_bot \
  nonebot_plugin_qfun \
  nonebot_plugin_qlicense
do
  rm -rf "/home/NoneBot/qinex/src/qinex/plugins/$d"
  cp -a "/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/$d" \
    "/home/NoneBot/qinex/src/qinex/plugins/$d"
done

rm -rf /home/NoneBot/qinex/知识库
cp -a /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/知识库 /home/NoneBot/qinex/知识库
```

## 4. GitHub 网络不可用时：本地打包上传

在 Windows 本地 PowerShell 执行：

```powershell
cd F:\code\nonebot\qinex
git archive --format=zip --output F:\code\nonebot\qinex-update.zip HEAD
scp F:\code\nonebot\qinex-update.zip root@qine:/tmp/qguard-main.zip
```

不要直接压缩整个工作目录。`git archive` 只会打包已经提交到 Git 的源码和文档，可以避免把本地 `.env`、提示词设计稿、临时压缩包、数据库等文件带到服务器或 GitHub。

在服务器执行：

```bash
cd /home/NoneBot

rm -rf /tmp/qguard_update
mkdir -p /tmp/qguard_update
python3 -m zipfile -e /tmp/qguard-main.zip /tmp/qguard_update

rm -rf /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard
mkdir -p /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard

if [ -d /tmp/qguard_update/qinex-nonebot-plugin-qguard-main ]; then
  cp -a /tmp/qguard_update/qinex-nonebot-plugin-qguard-main/. \
    /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/
else
  cp -a /tmp/qguard_update/. \
    /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/
fi

cd /home/NoneBot/qinex

for d in \
  nonebot_plugin_qguard \
  nonebot_plugin_ai_core \
  nonebot_plugin_log_doctor \
  nonebot_plugin_group_wiki \
  nonebot_plugin_support_bot \
  nonebot_plugin_qfun \
  nonebot_plugin_qlicense
do
  rm -rf "/home/NoneBot/qinex/src/qinex/plugins/$d"
  cp -a "/home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/$d" \
    "/home/NoneBot/qinex/src/qinex/plugins/$d"
done

rm -rf /home/NoneBot/qinex/知识库
cp -a /home/NoneBot/plugins-src/qinex-nonebot-plugin-qguard/知识库 /home/NoneBot/qinex/知识库
```

## 5. 环境变量

把仓库 `.env.example` 里的变量合并到 `/home/NoneBot/qinex/.env`。最重要的是：

```env
QGUARD_SUPER_ADMINS=[1348984838]
AI_CORE_API_KEY=sk-change-me
SUPPORT_BOT_ADMINS=[1348984838]

QLICENSE_API_BASE_URL=https://license.example.com
QLICENSE_BOT_ID=qinex-nonebot
QLICENSE_API_SECRET=change-me-to-a-long-shared-secret
QLICENSE_REQUIRE_SECURE_TRANSPORT=true
```

`QLICENSE_API_SECRET` 必须和授权服务端的 `LICENSE_BOT_API_SECRET` 完全一致。

## 6. 授权服务端配套配置

授权服务不在本仓库提交和发布，但机器人需要它提供内部 API。授权服务端至少要配置：

```env
LICENSE_BOT_ID=qinex-nonebot
LICENSE_BOT_API_SECRET=change-me-to-a-long-shared-secret
P4_PRIVKEY_PATH=/absolute/path/to/p4_license_private.pem
LICENSE_DEFAULT_S3_QUOTA=1
LICENSE_DEFAULT_P4_QUOTA=0
```

注意：

- `P4_PRIVKEY_PATH` 是授权服务端私钥路径，不要放进机器人仓库。
- P4 私钥必须和 P4 固件内置公钥是一对。
- P4 默认配额建议先保持 `0`，由主人用 `/授权 配额 QQ 数量 P4` 单独放行；如果你想所有用户默认可登记一块 P4，再设置 `LICENSE_DEFAULT_P4_QUOTA=1` 或群里执行 `/授权 默认配额 1 P4`。

## 7. 重启 NoneBot

如果你用 `screen`：

```bash
screen -S qinex -X quit 2>/dev/null || true
cd /home/NoneBot/qinex
source .venv/bin/activate
screen -S qinex -dm bash -lc 'cd /home/NoneBot/qinex && source .venv/bin/activate && nb run'
screen -r qinex
```

如果你用 systemd，请替换为自己的服务名：

```bash
systemctl restart qinex-nonebot
journalctl -u qinex-nonebot -f
```

## 8. 升级后验证

在群里依次测试：

```text
/管 状态
/管 插件
/管 帮助
/ai状态
/ai测试 用一句话介绍你自己
/知识 导入本地
/知识 搜索 P4
/客服 状态
/词云 状态
```

授权登记测试：

```text
/授权 查询 1348984838
/授权 配额 1348984838 2 S3
/授权 配额 1348984838 1 P4
/授权 默认配额 0 P4
/授权 预检 P4 AA:BB:CC:DD:EE:FF
/激活 P4 AA:BB:CC:DD:EE:FF
```

`/激活 P4 MAC` 成功后，用户还需要到 P4 板子专属配置页里联网并点击“在线激活”。MAC 必须从板子配置页复制，不要用电脑网卡、路由器列表或手机蓝牙里的 MAC。

## 9. 回滚

如果升级后启动失败：

```bash
cd /home/NoneBot/qinex
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_qguard
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_ai_core
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_log_doctor
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_group_wiki
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_support_bot
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_qfun
rm -rf /home/NoneBot/qinex/src/qinex/plugins/nonebot_plugin_qlicense
```

再从备份源码目录复制上一版插件，或用 git 回到上一 commit。数据库文件在 `data/` 下，升级前可以先备份：

```bash
cd /home/NoneBot/qinex
tar czf /home/NoneBot/qinex-data-backup-$(date +%F-%H%M%S).tar.gz data
```
