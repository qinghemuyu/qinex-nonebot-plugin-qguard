# nonebot-plugin-qguard

QGuard 是一个基于 NoneBot 2 + OneBot v11 的 QQ 群安全管理插件。

当前实现覆盖 v0.1 + v0.2：

- 基础群管：帮助、状态、开启/关闭、禁言、解禁、踢人、踢黑、警告、撤回、查用户、最近日志。
- 群名片：设置名片、清空名片、查询名片。
- 群名片锁：锁定、解锁、列表、扫描、修复、定时巡检。
- 审计日志：成功、失败、权限不足和自动修复都会记录。
- 权限系统：普通成员、可信成员、小管理、群管理员、群主、超级管理员。

## 安装

```bash
pip install -e .
```

## 配置

复制 `.env.example` 到你的 NoneBot 项目 `.env`，按需修改：

```env
QGUARD_DB_URL=sqlite+aiosqlite:///./data/qguard.db
QGUARD_SUPER_ADMINS=[1348984838]
QGUARD_COMMAND_PREFIX=/管
```

## 命令列表

```text
/管 帮助
/管 状态
/管 开启
/管 关闭
/管 禁 @用户 10m 原因
/管 解禁 @用户
/管 踢 @用户 原因
/管 踢黑 @用户 原因
/管 警告 @用户 原因
/管 撤回
/管 查 @用户
/管 日志 最近
/管 名片 @用户 新名片
/管 清名片 @用户
/管 名片查 @用户
/管 名片锁 @用户 固定名片
/管 名片解锁 @用户
/管 名片锁列表
/管 名片扫描
/管 名片修复
/管 名片锁全群 开
/管 名片锁全群 关
```

## 权限说明

权限来源优先级：

```text
QGUARD_SUPER_ADMINS > member_profile.role > OneBot 群成员 role > 普通成员
```

管理员不能处罚群主，也不能处罚同级或更高等级成员。权限不足会写入 `audit_log`。

## 群名片锁说明

名片锁使用三层兜底：

- 兼容 OneBot 实现端可能上报的 `group_card` 扩展通知。
- 定时巡检 `get_group_member_list`。
- 群消息事件中抽样检查发言人的名片。

同一 `group_id:user_id` 会加异步锁，插件刚修复过名片后的短时间内会忽略重复事件，避免死循环。

## 数据库说明

启动时会自动创建以下表：

- `group_config`
- `member_profile`
- `card_lock`
- `blacklist`
- `whitelist`
- `message_cache`
- `audit_log`

## 开发计划

- v0.3：关键词/正则自动审核。
- v0.4：新人保护与入群审核。
- v0.5：群设置保护与综合巡检。
