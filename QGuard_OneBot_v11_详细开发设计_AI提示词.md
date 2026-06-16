# QGuard OneBot v11 QQ 群管插件：详细开发设计与 AI 提示词文档

> 项目名：`nonebot-plugin-qguard`  
> Python 模块名：`nonebot_plugin_qguard`  
> 技术栈：NoneBot 2 + nonebot-adapter-onebot v11 + SQLAlchemy Async + SQLite/PostgreSQL + APScheduler  
> 目标：开发一个可长期运行、可扩展、可审计的 QQ 群管插件，第一阶段只支持 OneBot v11。

---

## 0. 重要结论

本插件第一阶段**只支持 OneBot v11**，不考虑 QQ 官方机器人适配器，不做多适配器兼容。  
原因：QQ群管核心动作依赖禁言、踢人、撤回、设置群名片、读取群成员列表、处理加群请求等能力，OneBot v11 生态更适合优先实现完整群管闭环。

本插件必须优先完成：

1. 基础群管命令：禁言、解禁、踢人、踢黑、撤回、警告、查用户、日志。
2. 群名片管理：设置群名片、清空群名片、批量规范名片。
3. 群名片锁：锁定群名片、防止群员修改、自动改回、定时巡检。
4. 权限系统：超级管理员、群主、群管理员、小管理、可信用户、普通成员。
5. 审计日志：所有人工操作、自动操作、失败操作都必须记录。
6. 自动审核雏形：关键词规则、自动撤回、自动禁言、违规积分。

---

## 1. 官方能力依据

开发时请以以下官方能力为准：

- NoneBot 插件推荐命名：项目名建议 `nonebot-plugin-*`，模块名建议 `nonebot_plugin_*`。
- NoneBot OneBot v11 适配器提供 OneBot v11 协议适配。
- OneBot v11 Bot API 提供：
  - `send_group_msg`
  - `delete_msg`
  - `get_msg`
  - `set_group_kick`
  - `set_group_ban`
  - `set_group_whole_ban`
  - `set_group_admin`
  - `set_group_anonymous`
  - `set_group_card`
  - `set_group_name`
  - `set_group_special_title`
  - `set_group_add_request`
  - `get_group_info`
  - `get_group_member_info`
  - `get_group_member_list`
- OneBot v11 标准通知事件包含：
  - 群文件上传
  - 群管理员变动
  - 群成员减少
  - 群成员增加
  - 群禁言
  - 群消息撤回
  - 群内戳一戳
  - 群成员荣誉变更
- 注意：标准 OneBot v11 通知事件里**不能稳定假设一定存在群名片变更事件**。部分实现端可能有 `group_card` 扩展事件，但不能依赖它作为唯一机制。因此“防止群员改名片”必须采用：
  - 扩展事件监听，如果实现端上报则立即处理。
  - 定时巡检 `get_group_member_list`，发现名片变化后自动改回。
  - 用户发言时抽样检查当前成员名片，作为兜底。

---

## 2. 插件定位

QGuard 是一个基于 NoneBot 2 + OneBot v11 的 QQ 群安全管理插件，支持：

1. 人工群管
2. 自动风控
3. 群名片修改
4. 群名片锁定防修改
5. 群设置保护
6. 反广告
7. 反刷屏
8. 关键词/正则规则
9. 新人保护
10. 加群审核
11. 违规积分
12. 分级处罚
13. 消息缓存
14. 操作审计
15. 定时巡检

核心设计原则：

```text
命令层只负责解析参数和回复用户。
业务层负责权限、规则、处罚、日志。
适配器层负责调用 OneBot v11 API。
任何命令不得直接调用 bot.set_group_ban / bot.set_group_card 等 API。
所有群操作必须经过 GroupOps 和对应 service。
所有处罚和修复操作必须写入 audit_log。
```

---

## 3. 插件功能范围

### 3.1 v0.1 基础群管

必须实现：

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
```

### 3.2 v0.2 群名片管理与名片锁

必须实现：

```text
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

名片锁要求：

1. 可以锁定某个用户的群名片。
2. 用户修改后自动改回。
3. 支持定时巡检。
4. 支持手动扫描。
5. 支持手动修复。
6. 修复失败必须记录失败原因。
7. 防止死循环。
8. 防止并发重复修改。

### 3.3 v0.3 自动审核

必须实现：

```text
/管 规则 添加 关键词 xxx 警告
/管 规则 添加 关键词 xxx 禁言10m
/管 规则 添加 正则 xxx 踢出
/管 规则 删除 ID
/管 规则 列表
/管 规则 测试 文本
/管 广告检测 开
/管 广告检测 关
/管 刷屏检测 开
/管 刷屏检测 关
```

### 3.4 v0.4 新人保护和加群审核

必须实现：

```text
/管 新人保护 开
/管 新人保护 关
/管 新人保护 时长 24h
/管 新人禁链接 开
/管 新人禁图片 开
/管 入群审核 开
/管 入群审核 关
/管 入群暗号 设置 xxx
/管 入群拒绝理由 设置 xxx
```

### 3.5 v0.5 群设置保护和巡检

必须实现：

```text
/管 群名 设置 新群名
/管 群名锁 开 新群名
/管 群名锁 关
/管 群名修复
/管 匿名 开
/管 匿名 关
/管 匿名锁 开 关
/管 头衔 @用户 头衔
/管 巡检
/管 巡检 名片
/管 巡检 权限
/管 自动巡检 开
/管 自动巡检 间隔 10m
```

---

## 4. 项目目录结构

AI 生成代码时必须使用这个结构。

```text
nonebot-plugin-qguard/
├── nonebot_plugin_qguard/
│   ├── __init__.py
│   ├── config.py
│   ├── metadata.py
│   ├── constants.py
│   ├── enums.py
│   │
│   ├── adapter/
│   │   ├── __init__.py
│   │   ├── group_ops.py
│   │   └── onebot_v11_ops.py
│   │
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── root.py
│   │   ├── punish.py
│   │   ├── card.py
│   │   ├── card_lock.py
│   │   ├── rule.py
│   │   ├── score.py
│   │   ├── whitelist.py
│   │   ├── blacklist.py
│   │   ├── group_setting.py
│   │   ├── join_review.py
│   │   └── audit.py
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── message_handler.py
│   │   ├── notice_handler.py
│   │   └── request_handler.py
│   │
│   ├── services/
│   │   ├── permission_service.py
│   │   ├── group_config_service.py
│   │   ├── punishment_service.py
│   │   ├── card_service.py
│   │   ├── card_lock_service.py
│   │   ├── rule_engine.py
│   │   ├── anti_spam_service.py
│   │   ├── anti_ad_service.py
│   │   ├── join_review_service.py
│   │   ├── score_service.py
│   │   ├── audit_service.py
│   │   ├── message_cache_service.py
│   │   └── patrol_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── group_config_repo.py
│   │   ├── member_repo.py
│   │   ├── card_lock_repo.py
│   │   ├── rule_repo.py
│   │   ├── score_repo.py
│   │   ├── blacklist_repo.py
│   │   ├── whitelist_repo.py
│   │   ├── message_cache_repo.py
│   │   └── audit_log_repo.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── group_config.py
│   │   ├── member_profile.py
│   │   ├── card_lock.py
│   │   ├── rule.py
│   │   ├── blacklist.py
│   │   ├── whitelist.py
│   │   ├── message_cache.py
│   │   └── audit_log.py
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── patrol_jobs.py
│   │   ├── cleanup_jobs.py
│   │   └── card_lock_jobs.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── timeparse.py
│       ├── message_parser.py
│       ├── cqcode.py
│       ├── regex_safe.py
│       ├── locks.py
│       └── formatter.py
│
├── tests/
│   ├── test_timeparse.py
│   ├── test_permission.py
│   ├── test_card_lock.py
│   └── test_rule_engine.py
│
├── pyproject.toml
├── README.md
└── .env.example
```

---

## 5. 配置设计

### 5.1 `.env.example`

```env
DRIVER=~fastapi+~websockets
HOST=127.0.0.1
PORT=8080

ONEBOT_V11_ACCESS_TOKEN=change-me-to-a-long-random-token

QGUARD_DB_URL=sqlite+aiosqlite:///./data/qguard.db
QGUARD_SUPER_ADMINS=[123456789]
QGUARD_DEFAULT_ENABLE=true
QGUARD_DEFAULT_MUTE_SECONDS=600
QGUARD_MESSAGE_CACHE_DAYS=7
QGUARD_CARD_LOCK_PATROL_INTERVAL_SECONDS=600
QGUARD_AUTO_PATROL_INTERVAL_SECONDS=1800
QGUARD_ENABLE_AUTO_MODERATION=true
QGUARD_ENABLE_MESSAGE_CACHE=true
QGUARD_COMMAND_PREFIX=/管
```

### 5.2 `config.py`

必须使用 Pydantic 配置类。字段：

```python
from pydantic import BaseModel, Field

class Config(BaseModel):
    qguard_db_url: str = "sqlite+aiosqlite:///./data/qguard.db"
    qguard_super_admins: set[int] = Field(default_factory=set)
    qguard_default_enable: bool = True
    qguard_default_mute_seconds: int = 600
    qguard_message_cache_days: int = 7
    qguard_card_lock_patrol_interval_seconds: int = 600
    qguard_auto_patrol_interval_seconds: int = 1800
    qguard_enable_auto_moderation: bool = True
    qguard_enable_message_cache: bool = True
    qguard_command_prefix: str = "/管"
```

---

## 6. PluginMetadata

`metadata.py`：

```python
from nonebot.plugin import PluginMetadata
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QGuard 群管",
    description="基于 NoneBot 2 + OneBot v11 的 QQ 群安全管理插件，支持禁言、踢人、撤回、群名片锁、自动审核、日志审计。",
    usage="""
/管 帮助
/管 状态
/管 禁 @用户 10m 原因
/管 名片 @用户 新名片
/管 名片锁 @用户 固定名片
/管 名片扫描
/管 规则 添加 关键词 xxx 禁言10m
""",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
```

`__init__.py` 必须导入 metadata 和所有 handler / command 模块。

---

## 7. 枚举设计

`enums.py`：

```python
from enum import IntEnum, StrEnum

class QGuardRole(IntEnum):
    MEMBER = 0
    TRUSTED = 1
    MINI_ADMIN = 2
    GROUP_ADMIN = 3
    GROUP_OWNER = 4
    SUPER_ADMIN = 5

class AuditAction(StrEnum):
    ENABLE_GROUP = "enable_group"
    DISABLE_GROUP = "disable_group"
    WARN = "warn"
    MUTE = "mute"
    UNMUTE = "unmute"
    KICK = "kick"
    KICK_BLACK = "kick_black"
    DELETE_MSG = "delete_msg"
    SET_CARD = "set_card"
    CLEAR_CARD = "clear_card"
    LOCK_CARD = "lock_card"
    UNLOCK_CARD = "unlock_card"
    FIX_CARD = "fix_card"
    SCAN_CARD = "scan_card"
    ADD_RULE = "add_rule"
    DELETE_RULE = "delete_rule"
    HIT_RULE = "hit_rule"
    JOIN_APPROVE = "join_approve"
    JOIN_REJECT = "join_reject"
    PATROL = "patrol"

class RuleType(StrEnum):
    KEYWORD = "keyword"
    REGEX = "regex"
    LINK = "link"
    SPAM = "spam"
    CARD_REGEX = "card_regex"

class RuleAction(StrEnum):
    NONE = "none"
    WARN = "warn"
    DELETE = "delete"
    MUTE = "mute"
    KICK = "kick"
    KICK_BLACK = "kick_black"
    FIX_CARD = "fix_card"

class AuditResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
```

---

## 8. 数据库模型设计

必须使用 SQLAlchemy 2.0 async 风格。

### 8.1 group_config

```sql
group_id BIGINT PRIMARY KEY
enabled BOOLEAN NOT NULL DEFAULT TRUE
auto_moderation_enabled BOOLEAN NOT NULL DEFAULT TRUE
anti_ad_enabled BOOLEAN NOT NULL DEFAULT FALSE
anti_spam_enabled BOOLEAN NOT NULL DEFAULT FALSE
keyword_check_enabled BOOLEAN NOT NULL DEFAULT TRUE
new_member_protection_enabled BOOLEAN NOT NULL DEFAULT FALSE
join_review_enabled BOOLEAN NOT NULL DEFAULT FALSE
card_lock_enabled BOOLEAN NOT NULL DEFAULT TRUE
group_name_lock_enabled BOOLEAN NOT NULL DEFAULT FALSE
anonymous_lock_enabled BOOLEAN NOT NULL DEFAULT FALSE
message_cache_enabled BOOLEAN NOT NULL DEFAULT TRUE
default_mute_seconds INTEGER NOT NULL DEFAULT 600
card_lock_patrol_interval_seconds INTEGER NOT NULL DEFAULT 600
created_at DATETIME NOT NULL
updated_at DATETIME NOT NULL
```

### 8.2 member_profile

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NOT NULL
user_id BIGINT NOT NULL
role INTEGER NOT NULL DEFAULT 0
trust_level INTEGER NOT NULL DEFAULT 0
warning_score INTEGER NOT NULL DEFAULT 0
warning_count INTEGER NOT NULL DEFAULT 0
mute_count INTEGER NOT NULL DEFAULT 0
kick_count INTEGER NOT NULL DEFAULT 0
join_time DATETIME NULL
newbie_until DATETIME NULL
last_active_at DATETIME NULL
created_at DATETIME NOT NULL
updated_at DATETIME NOT NULL
UNIQUE(group_id, user_id)
```

### 8.3 card_lock

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NOT NULL
user_id BIGINT NOT NULL
locked_card VARCHAR(128) NOT NULL
enabled BOOLEAN NOT NULL DEFAULT TRUE
template_id INTEGER NULL
violation_count INTEGER NOT NULL DEFAULT 0
last_seen_card VARCHAR(128) NULL
last_fixed_at DATETIME NULL
last_error TEXT NULL
created_by BIGINT NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NOT NULL
UNIQUE(group_id, user_id)
```

### 8.4 rule

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NOT NULL
rule_type VARCHAR(32) NOT NULL
pattern TEXT NOT NULL
action VARCHAR(32) NOT NULL
score_delta INTEGER NOT NULL DEFAULT 0
mute_seconds INTEGER NOT NULL DEFAULT 0
delete_message BOOLEAN NOT NULL DEFAULT FALSE
enabled BOOLEAN NOT NULL DEFAULT TRUE
priority INTEGER NOT NULL DEFAULT 100
created_by BIGINT NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NOT NULL
```

### 8.5 blacklist

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NULL
user_id BIGINT NOT NULL
reason TEXT NULL
created_by BIGINT NOT NULL
expires_at DATETIME NULL
created_at DATETIME NOT NULL
UNIQUE(group_id, user_id)
```

`group_id = NULL` 表示全局黑名单。

### 8.6 whitelist

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NOT NULL
user_id BIGINT NOT NULL
reason TEXT NULL
created_by BIGINT NOT NULL
created_at DATETIME NOT NULL
UNIQUE(group_id, user_id)
```

### 8.7 message_cache

```sql
message_id BIGINT PRIMARY KEY
group_id BIGINT NOT NULL
user_id BIGINT NOT NULL
plain_text TEXT NULL
raw_message_json TEXT NULL
image_count INTEGER NOT NULL DEFAULT 0
at_count INTEGER NOT NULL DEFAULT 0
link_count INTEGER NOT NULL DEFAULT 0
created_at DATETIME NOT NULL
expires_at DATETIME NOT NULL
```

### 8.8 audit_log

```sql
id INTEGER PRIMARY KEY
group_id BIGINT NULL
operator_id BIGINT NULL
target_user_id BIGINT NULL
action VARCHAR(64) NOT NULL
reason TEXT NULL
result VARCHAR(32) NOT NULL
error_message TEXT NULL
related_message_id BIGINT NULL
related_rule_id INTEGER NULL
metadata_json TEXT NULL
created_at DATETIME NOT NULL
```

---

## 9. GroupOps 适配器层

### 9.1 设计要求

业务层不得直接调用 OneBot API。必须通过 `GroupOps`。

`adapter/group_ops.py`：

```python
from abc import ABC, abstractmethod
from typing import Any

class GroupOps(ABC):
    @abstractmethod
    async def send_group_msg(self, group_id: int, message: str) -> Any: ...

    @abstractmethod
    async def delete_msg(self, message_id: int) -> None: ...

    @abstractmethod
    async def get_msg(self, message_id: int) -> dict[str, Any]: ...

    @abstractmethod
    async def mute(self, group_id: int, user_id: int, seconds: int) -> None: ...

    @abstractmethod
    async def unmute(self, group_id: int, user_id: int) -> None: ...

    @abstractmethod
    async def kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None: ...

    @abstractmethod
    async def whole_mute(self, group_id: int, enable: bool) -> None: ...

    @abstractmethod
    async def set_group_card(self, group_id: int, user_id: int, card: str) -> None: ...

    @abstractmethod
    async def set_group_name(self, group_id: int, name: str) -> None: ...

    @abstractmethod
    async def set_group_admin(self, group_id: int, user_id: int, enable: bool) -> None: ...

    @abstractmethod
    async def set_group_anonymous(self, group_id: int, enable: bool) -> None: ...

    @abstractmethod
    async def set_special_title(self, group_id: int, user_id: int, title: str, duration: int = -1) -> None: ...

    @abstractmethod
    async def get_group_info(self, group_id: int, no_cache: bool = True) -> dict[str, Any]: ...

    @abstractmethod
    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True) -> dict[str, Any]: ...

    @abstractmethod
    async def get_group_member_list(self, group_id: int) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def handle_group_add_request(self, flag: str, sub_type: str, approve: bool, reason: str = "") -> None: ...
```

### 9.2 `onebot_v11_ops.py`

实现时捕获异常，不要吞掉异常，应向上抛出业务层可识别的异常，或者包装成 `QGuardActionError`。

```python
from typing import Any
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.exception import ActionFailed, NetworkError
from .group_ops import GroupOps

class QGuardActionError(RuntimeError):
    pass

class OneBotV11GroupOps(GroupOps):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_group_msg(self, group_id: int, message: str) -> Any:
        return await self.bot.send_group_msg(group_id=group_id, message=message)

    async def delete_msg(self, message_id: int) -> None:
        await self.bot.delete_msg(message_id=message_id)

    async def get_msg(self, message_id: int) -> dict[str, Any]:
        return await self.bot.get_msg(message_id=message_id)

    async def mute(self, group_id: int, user_id: int, seconds: int) -> None:
        await self.bot.set_group_ban(group_id=group_id, user_id=user_id, duration=seconds)

    async def unmute(self, group_id: int, user_id: int) -> None:
        await self.bot.set_group_ban(group_id=group_id, user_id=user_id, duration=0)

    async def kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        await self.bot.set_group_kick(
            group_id=group_id,
            user_id=user_id,
            reject_add_request=reject_add_request,
        )

    async def whole_mute(self, group_id: int, enable: bool) -> None:
        await self.bot.set_group_whole_ban(group_id=group_id, enable=enable)

    async def set_group_card(self, group_id: int, user_id: int, card: str) -> None:
        await self.bot.set_group_card(group_id=group_id, user_id=user_id, card=card)

    async def set_group_name(self, group_id: int, name: str) -> None:
        await self.bot.set_group_name(group_id=group_id, group_name=name)

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool) -> None:
        await self.bot.set_group_admin(group_id=group_id, user_id=user_id, enable=enable)

    async def set_group_anonymous(self, group_id: int, enable: bool) -> None:
        await self.bot.set_group_anonymous(group_id=group_id, enable=enable)

    async def set_special_title(self, group_id: int, user_id: int, title: str, duration: int = -1) -> None:
        await self.bot.set_group_special_title(
            group_id=group_id,
            user_id=user_id,
            special_title=title,
            duration=duration,
        )

    async def get_group_info(self, group_id: int, no_cache: bool = True) -> dict[str, Any]:
        return await self.bot.get_group_info(group_id=group_id, no_cache=no_cache)

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True) -> dict[str, Any]:
        return await self.bot.get_group_member_info(group_id=group_id, user_id=user_id, no_cache=no_cache)

    async def get_group_member_list(self, group_id: int) -> list[dict[str, Any]]:
        return await self.bot.get_group_member_list(group_id=group_id)

    async def handle_group_add_request(self, flag: str, sub_type: str, approve: bool, reason: str = "") -> None:
        await self.bot.set_group_add_request(
            flag=flag,
            sub_type=sub_type,
            approve=approve,
            reason=reason,
        )
```

---

## 10. 权限系统设计

### 10.1 权限等级

```text
0 普通成员 MEMBER
1 可信成员 TRUSTED
2 小管理 MINI_ADMIN
3 群管理员 GROUP_ADMIN
4 群主 GROUP_OWNER
5 超级管理员 SUPER_ADMIN
```

### 10.2 命令权限

```text
/管 帮助：0+
/管 状态：1+
/管 查：1+
/管 警告：2+
/管 禁：3+
/管 解禁：3+
/管 撤回：3+
/管 踢：3+
/管 踢黑：4+
/管 名片：3+
/管 清名片：3+
/管 名片锁：4+
/管 名片解锁：4+
/管 名片修复：4+
/管 名片锁全群：4+
/管 规则管理：4+
/管 群设置保护：4+
/管 设置管理员：5
/管 关闭：4+
```

### 10.3 越权保护

必须实现：

1. 普通成员不能使用管理命令。
2. 小管理不能踢人。
3. 群管理员不能处罚群主。
4. 群管理员不能处罚同级或更高级管理员。
5. 自动审核不能处罚超级管理员、群主、白名单成员。
6. 机器人不能操作权限高于自己的用户；如果操作失败，要明确回复“权限不足”。
7. 所有权限不足都要写入 audit_log，result 为 `skipped` 或 `failed`。

### 10.4 获取角色逻辑

优先级：

```text
QGUARD_SUPER_ADMINS 配置
  > 插件 member_profile.role
  > OneBot 群成员 role 字段 owner/admin/member
  > 默认普通成员
```

---

## 11. 命令解析设计

推荐统一使用 `/管` 作为根命令，避免命令污染。

### 11.1 根命令

`commands/root.py`：

```text
/管 帮助
/管 状态
/管 开启
/管 关闭
```

### 11.2 处罚命令

`commands/punish.py`：

```text
/管 禁 @用户 10m 原因
/管 解禁 @用户
/管 踢 @用户 原因
/管 踢黑 @用户 原因
/管 警告 @用户 原因
/管 撤回
```

解析要求：

1. 支持 `@用户`。
2. 支持纯 QQ 号。
3. `/管 撤回` 必须要求回复某条消息；如果没有 reply，提示用户。
4. 时间支持：`10s`、`10m`、`2h`、`1d`、`永久`。
5. 原因可以为空，默认“未填写原因”。

### 11.3 名片命令

`commands/card.py`：

```text
/管 名片 @用户 新名片
/管 清名片 @用户
/管 名片查 @用户
```

### 11.4 名片锁命令

`commands/card_lock.py`：

```text
/管 名片锁 @用户 固定名片
/管 名片解锁 @用户
/管 名片锁列表
/管 名片扫描
/管 名片修复
/管 名片锁全群 开
/管 名片锁全群 关
```

---

## 12. 群名片锁详细逻辑

这是本插件第一阶段的核心功能之一。

### 12.1 锁定名片

命令：

```text
/管 名片锁 @用户 固定名片
```

流程：

```text
解析目标用户和固定名片
  ↓
检查操作者权限 >= GROUP_OWNER
  ↓
检查目标用户不能高于操作者
  ↓
调用 set_group_card 立即设置名片
  ↓
写入 card_lock 表
  ↓
写入 audit_log
  ↓
回复成功
```

### 12.2 解锁名片

命令：

```text
/管 名片解锁 @用户
```

流程：

```text
检查权限
  ↓
将 card_lock.enabled 设为 false
  ↓
写 audit_log
  ↓
回复成功
```

### 12.3 自动修复名片

触发来源：

1. 实现端扩展事件 `group_card`。
2. 定时任务巡检。
3. 用户发言时抽样检测。
4. 手动 `/管 名片修复`。

处理流程：

```text
读取 group_config.card_lock_enabled
  ↓
读取 card_lock
  ↓
获取当前群名片
  ↓
当前名片 == locked_card？
  ├─ 是：更新 last_seen_card 后结束
  └─ 否：调用 set_group_card 改回
          ↓
        violation_count + 1
          ↓
        写 audit_log
          ↓
        如配置处罚则警告/禁言
```

### 12.4 防止死循环

必须实现：

1. 使用 `asyncio.Lock`，按 `group_id:user_id` 加锁。
2. 插件刚修改过名片后，10 秒内忽略同一用户的名片变更事件。
3. 连续失败 3 次后，不要无限重试，写入 `last_error` 并通知管理员。
4. 名片为空时也算变更，除非 locked_card 也是空。
5. `set_group_card` 失败不能导致整个事件处理器崩溃。

### 12.5 定时巡检

使用 `nonebot-plugin-apscheduler`。

巡检逻辑：

```text
每 N 分钟执行一次
  ↓
查询开启 card_lock_enabled 的群
  ↓
获取群成员列表 get_group_member_list
  ↓
读取该群所有 enabled=true 的 card_lock
  ↓
逐个对比当前 card 与 locked_card
  ↓
不一致则限速修复
  ↓
记录扫描数量、修复数量、失败数量
```

限速要求：

```text
每个群每秒最多 1 次 set_group_card
每次巡检最多修复 50 人
超过 50 人则记录并下次继续
```

---

## 13. 处罚服务设计

`services/punishment_service.py`

所有处罚都必须走这个服务。

### 13.1 方法

```python
class PunishmentService:
    async def warn(self, ops, group_id, operator_id, target_user_id, reason, related_message_id=None): ...
    async def mute(self, ops, group_id, operator_id, target_user_id, seconds, reason, related_message_id=None): ...
    async def unmute(self, ops, group_id, operator_id, target_user_id, reason): ...
    async def kick(self, ops, group_id, operator_id, target_user_id, reason, reject_add_request=False): ...
    async def delete_msg(self, ops, group_id, operator_id, message_id, reason): ...
```

### 13.2 要求

每个方法必须：

1. 检查权限。
2. 检查插件是否开启。
3. 调用 GroupOps。
4. 更新 member_profile。
5. 写入 audit_log。
6. 返回结构化结果。
7. 失败时写日志，不假装成功。

返回对象：

```python
class ActionResult(BaseModel):
    success: bool
    action: str
    message: str
    error: str | None = None
```

---

## 14. 审计日志设计

所有关键动作必须写日志。

### 14.1 必须记录的动作

```text
插件开启/关闭
禁言/解禁
踢人/踢黑
警告
撤回
设置名片
清空名片
锁定名片
解除名片锁
自动修复名片
规则命中
规则新增/删除
加群通过/拒绝
巡检
API 调用失败
权限不足
```

### 14.2 日志查询命令

```text
/管 日志 最近
/管 日志 @用户
/管 名片日志 @用户
/管 处罚日志 @用户
```

---

## 15. 消息缓存设计

`message_handler.py` 收到群消息后，优先缓存。

缓存字段：

```text
message_id
group_id
user_id
plain_text
raw_message_json
image_count
at_count
link_count
created_at
expires_at
```

用途：

1. 撤回后可追溯。
2. 自动审核有证据。
3. `/管 最近消息 @用户` 可查询。
4. 规则测试和误判复盘。

保留周期默认 7 天。

---

## 16. 自动审核设计

### 16.1 RuleEngine

`services/rule_engine.py`

输入：

```python
class MessageContext(BaseModel):
    group_id: int
    user_id: int
    message_id: int
    plain_text: str
    raw_message: Any
    image_count: int = 0
    at_count: int = 0
    link_count: int = 0
    is_new_member: bool = False
```

输出：

```python
class ModerationDecision(BaseModel):
    hit: bool
    rule_id: int | None = None
    rule_type: str | None = None
    action: str = "none"
    reason: str = ""
    score_delta: int = 0
    mute_seconds: int = 0
    delete_message: bool = False
```

### 16.2 检测顺序

```text
白名单检查
  ↓
群配置检查
  ↓
关键词规则
  ↓
正则规则
  ↓
广告链接检测
  ↓
刷屏检测
  ↓
新人限制
  ↓
生成决策
  ↓
处罚服务执行
```

### 16.3 默认保守策略

默认不要直接踢人。

```text
轻微违规：警告
明显广告：撤回 + 禁言 10 分钟
新人明显广告：撤回 + 禁言 1 小时
多次违规：按积分阶梯处罚
```

---

## 17. 加群审核设计

处理 OneBot v11 request 事件。

审核维度：

```text
是否黑名单
申请理由是否为空
申请理由是否包含广告
申请理由是否包含暗号
昵称是否命中规则
是否短时间重复申请
```

策略：

```text
黑名单：自动拒绝
必须暗号但不匹配：自动拒绝
命中广告：自动拒绝
低风险：自动通过或通知管理员，根据群配置决定
中风险：通知管理员
```

命令：

```text
/管 入群审核 开
/管 入群审核 关
/管 入群暗号 设置 xxx
/管 入群拒绝理由 设置 xxx
```

---

## 18. 时间解析工具

`utils/timeparse.py`

必须支持：

```text
10s
10m
2h
1d
永久
0
```

返回秒数：

```text
10s -> 10
10m -> 600
2h -> 7200
1d -> 86400
永久 -> 2592000 或配置的最大值
0 -> 0
```

注意：OneBot v11 禁言时长单位是秒，`0` 表示取消禁言。

---

## 19. 开发阶段拆分

AI 必须按阶段开发，不允许一口气乱写。

### 阶段 1：项目骨架

产出：

```text
pyproject.toml
README.md
.env.example
nonebot_plugin_qguard/__init__.py
config.py
metadata.py
enums.py
constants.py
```

验收：

```text
插件可以被 NoneBot 加载。
PluginMetadata 正常显示。
配置类可读取 .env。
```

### 阶段 2：数据库层

产出：

```text
models/*
repositories/*
数据库初始化逻辑
```

验收：

```text
启动时可创建表。
可读写 group_config。
可读写 card_lock。
可写 audit_log。
```

### 阶段 3：GroupOps 层

产出：

```text
adapter/group_ops.py
adapter/onebot_v11_ops.py
```

验收：

```text
所有 OneBot v11 API 调用都被封装。
业务代码不直接依赖 Bot API。
```

### 阶段 4：权限与审计

产出：

```text
services/permission_service.py
services/audit_service.py
```

验收：

```text
可以判断超级管理员、群主、群管理员、普通成员。
权限不足会返回明确结果。
所有失败/跳过都能写日志。
```

### 阶段 5：基础群管命令

产出：

```text
commands/root.py
commands/punish.py
services/punishment_service.py
```

验收：

```text
/管 帮助 可用
/管 状态 可用
/管 开启/关闭 可用
/管 禁 可用
/管 解禁 可用
/管 踢 可用
/管 踢黑 可用
/管 撤回 可用
所有操作都写日志
```

### 阶段 6：群名片管理

产出：

```text
commands/card.py
services/card_service.py
```

验收：

```text
/管 名片 @用户 新名片 可用
/管 清名片 @用户 可用
/管 名片查 @用户 可用
所有操作写日志
```

### 阶段 7：群名片锁

产出：

```text
commands/card_lock.py
services/card_lock_service.py
scheduler/card_lock_jobs.py
utils/locks.py
```

验收：

```text
/管 名片锁 @用户 固定名片 可用
/管 名片解锁 @用户 可用
/管 名片锁列表 可用
/管 名片扫描 可用
/管 名片修复 可用
定时巡检可用
用户改名片后可自动改回
失败有日志
不会死循环
```

### 阶段 8：自动审核

产出：

```text
services/rule_engine.py
commands/rule.py
handlers/message_handler.py
services/message_cache_service.py
```

验收：

```text
关键词规则可新增/删除/列表
群消息可缓存
命中规则后可撤回/警告/禁言
白名单不会被处罚
```

---

## 20. AI 主提示词

把下面这段直接发给 AI，让它开始开发。

```text
你是资深 Python / NoneBot 2 / OneBot v11 插件开发工程师。请为我开发一个 QQ 群管插件，项目名为 nonebot-plugin-qguard，模块名为 nonebot_plugin_qguard。

技术栈：
- Python 3.11+
- NoneBot 2
- nonebot-adapter-onebot v11
- SQLAlchemy 2.0 async
- aiosqlite，后续可兼容 PostgreSQL
- nonebot-plugin-apscheduler
- Pydantic 配置

第一阶段只支持 OneBot v11，不需要兼容 QQ 官方机器人适配器，不需要兼容 OneBot v12。

硬性要求：
1. 必须使用清晰的插件目录结构。
2. 必须提供 PluginMetadata。
3. 所有 OneBot API 调用必须封装到 adapter/group_ops.py 和 adapter/onebot_v11_ops.py。
4. 命令层不得直接调用 bot.set_group_ban、bot.set_group_card、bot.delete_msg 等 API。
5. 所有人工处罚和自动处罚必须经过 punishment_service。
6. 所有群操作必须写入 audit_log，包括成功、失败、权限不足、跳过。
7. 必须实现权限系统：普通成员、可信成员、小管理、群管理员、群主、超级管理员。
8. 必须防止越权处罚：管理员不能处罚群主，不能处罚同级或更高级成员，自动审核不能处罚白名单/超级管理员/群主。
9. 群名片锁必须采用事件监听 + 定时巡检双保险，不能只依赖 group_card 事件。
10. 必须有防死循环机制：同一 group_id + user_id 加 asyncio.Lock，插件刚修改过名片后的短时间内忽略重复事件，连续失败不得无限重试。
11. 所有批量操作必须限速。
12. 代码必须有类型注解。
13. 每个文件职责清晰，不要把所有代码堆进 __init__.py。
14. 先输出完整目录结构和开发计划，再逐文件生成代码。
15. 每完成一个阶段，给出运行方式和验收方式。

请先实现 v0.1 + v0.2：

v0.1 基础群管：
- /管 帮助
- /管 状态
- /管 开启
- /管 关闭
- /管 禁 @用户 10m 原因
- /管 解禁 @用户
- /管 踢 @用户 原因
- /管 踢黑 @用户 原因
- /管 警告 @用户 原因
- /管 撤回，要求回复某条消息
- /管 查 @用户
- /管 日志 最近

v0.2 群名片管理与名片锁：
- /管 名片 @用户 新名片
- /管 清名片 @用户
- /管 名片查 @用户
- /管 名片锁 @用户 固定名片
- /管 名片解锁 @用户
- /管 名片锁列表
- /管 名片扫描
- /管 名片修复
- 定时名片巡检
- 用户改名片后自动改回

数据库表至少包括：
- group_config
- member_profile
- card_lock
- blacklist
- whitelist
- message_cache
- audit_log

请注意：标准 OneBot v11 通知事件不稳定保证存在群名片变更事件，部分实现端可能有扩展 group_card 事件。因此实现时可以兼容扩展事件，但必须以 get_group_member_list 定时巡检作为可靠兜底。

现在开始：先输出项目目录结构，然后从 pyproject.toml、.env.example、config.py、metadata.py、__init__.py 开始生成代码。
```

---

## 21. 阶段化追问提示词

如果 AI 一次没写完，用下面这些继续催它。

### 21.1 生成数据库层

```text
继续开发 QGuard。现在生成数据库层代码：models、repositories、数据库初始化逻辑。要求使用 SQLAlchemy 2.0 async，支持 sqlite+aiosqlite。必须实现 group_config、member_profile、card_lock、blacklist、whitelist、message_cache、audit_log。每个表要有 created_at / updated_at。请逐文件输出代码，并说明如何在插件启动时初始化数据库。
```

### 21.2 生成 GroupOps

```text
继续开发 QGuard。现在生成 adapter/group_ops.py 和 adapter/onebot_v11_ops.py。要求所有 OneBot v11 API 调用都封装在 OneBotV11GroupOps 中，包括 send_group_msg、delete_msg、get_msg、mute、unmute、kick、whole_mute、set_group_card、set_group_name、set_group_admin、set_group_anonymous、set_special_title、get_group_info、get_group_member_info、get_group_member_list、handle_group_add_request。业务层不得直接依赖 Bot API。
```

### 21.3 生成权限和审计服务

```text
继续开发 QGuard。现在生成 permission_service.py 和 audit_service.py。权限等级包括 MEMBER、TRUSTED、MINI_ADMIN、GROUP_ADMIN、GROUP_OWNER、SUPER_ADMIN。权限来源优先级：QGUARD_SUPER_ADMINS > 插件 member_profile.role > OneBot 群成员 role。必须实现越权检查，管理员不能处罚群主或同级/更高级成员。所有权限不足和操作失败都必须写 audit_log。
```

### 21.4 生成基础群管命令

```text
继续开发 QGuard。现在生成基础群管命令和 punishment_service。命令包括 /管 帮助、/管 状态、/管 开启、/管 关闭、/管 禁、/管 解禁、/管 踢、/管 踢黑、/管 警告、/管 撤回、/管 查、/管 日志 最近。要求支持 @用户 和 QQ 号，禁言时间支持 10s、10m、2h、1d、永久。/管 撤回 必须要求回复消息。所有操作必须写 audit_log。
```

### 21.5 生成群名片功能

```text
继续开发 QGuard。现在生成群名片管理和群名片锁功能。命令包括 /管 名片、/管 清名片、/管 名片查、/管 名片锁、/管 名片解锁、/管 名片锁列表、/管 名片扫描、/管 名片修复。要求通过 set_group_card 设置群名片，通过 get_group_member_info 查询当前名片。名片锁写入 card_lock 表，发现用户当前名片与 locked_card 不一致时自动改回。所有修复和失败必须写 audit_log。
```

### 21.6 生成定时巡检

```text
继续开发 QGuard。现在生成名片锁定时巡检。要求使用 nonebot-plugin-apscheduler。定时查询开启 card_lock_enabled 的群，调用 get_group_member_list 获取群成员列表，和 card_lock 表中的 locked_card 对比，不一致则通过 card_lock_service 自动修复。必须限速，每个群每秒最多 1 次 set_group_card，每次巡检最多修复 50 人。必须避免死循环和并发重复修复。
```

### 21.7 生成自动审核

```text
继续开发 QGuard。现在生成自动审核功能。实现 message_cache_service、rule_engine、commands/rule.py 和 handlers/message_handler.py。支持关键词规则和正则规则，命中后可以警告、撤回、禁言。命令包括 /管 规则 添加 关键词 xxx 警告、/管 规则 添加 关键词 xxx 禁言10m、/管 规则 添加 正则 xxx 踢出、/管 规则 删除 ID、/管 规则 列表、/管 规则 测试 文本。白名单、超级管理员、群主不得被自动处罚。
```

---

## 22. 代码质量要求

AI 生成代码时必须满足：

```text
1. Python 3.11+。
2. 使用类型注解。
3. 不写同步数据库调用。
4. 不在命令处理器里堆业务逻辑。
5. 不直接散落调用 OneBot API。
6. 不吞异常。
7. 所有用户可见错误要友好明确。
8. 所有内部错误要写日志。
9. 所有批量操作要限速。
10. 所有定时任务要可开关。
11. 所有规则要支持 enabled 字段。
12. 所有查询列表要限制数量，避免刷屏。
```

---

## 23. 验收清单

### 23.1 加载验收

```text
NoneBot 可以正常启动。
插件可以正常加载。
数据库表可以正常创建。
OneBot v11 机器人连接后不报错。
```

### 23.2 基础命令验收

```text
/管 帮助 正常返回帮助。
/管 状态 正常返回群配置状态。
/管 开启 可以开启本群插件。
/管 关闭 可以关闭本群插件。
/管 禁 @用户 10m 测试 可以禁言。
/管 解禁 @用户 可以解除禁言。
/管 踢 @用户 可以踢人。
/管 踢黑 @用户 可以踢人并拉黑。
/管 撤回 回复消息可以撤回。
```

### 23.3 名片验收

```text
/管 名片 @用户 新名片 可以修改群名片。
/管 清名片 @用户 可以清空群名片。
/管 名片查 @用户 可以查询当前名片。
/管 名片锁 @用户 固定名片 可以锁定名片。
用户自行修改名片后，插件能自动改回。
/管 名片扫描 能扫描异常名片。
/管 名片修复 能修复异常名片。
```

### 23.4 日志验收

```text
每个操作都能在 audit_log 看到。
成功有 success。
失败有 failed 和 error_message。
权限不足有 skipped 或 failed。
自动修复名片有 FIX_CARD 日志。
```

### 23.5 权限验收

```text
普通成员不能使用管理命令。
小管理不能踢人。
群管理员不能处罚群主。
群管理员不能处罚同级或更高等级成员。
超级管理员可以跨群管理。
白名单不会被自动处罚。
```

---

## 24. 常见坑位

### 24.1 机器人不是管理员

禁言、踢人、改群名片、撤回都可能失败。失败时必须告诉用户：

```text
操作失败：机器人权限不足，请确认机器人是群管理员，并且目标用户权限低于机器人。
```

### 24.2 名片字段差异

OneBot 群成员信息里通常有 `card` 和 `nickname`。判断当前展示名时建议：

```text
display_name = card if card else nickname
```

但名片锁应只比较 `card` 字段，不要拿 nickname 当 locked_card。

### 24.3 group_card 扩展事件不稳定

不要把名片锁完全绑定在 `group_card` 事件上。必须实现巡检。

### 24.4 批量改名片风控

不要一次性刷几十个 API。必须限速。

### 24.5 撤回消息

`/管 撤回` 建议只支持回复消息，不建议让用户手填 message_id，避免误操作。

### 24.6 自动审核误伤

默认策略必须保守，先警告和短禁言，不要默认踢人。

---

## 25. README 结构建议

AI 最后生成 README 时按这个结构：

```text
# nonebot-plugin-qguard

## 简介
## 功能
## 安装
## 配置
## OneBot v11 连接方式
## 命令列表
## 权限说明
## 群名片锁说明
## 自动审核说明
## 数据库说明
## 常见问题
## 开发计划
```

---

## 26. 最终交付标准

最终项目应该做到：

```text
1. 可以 pip install -e . 安装。
2. 可以被 NoneBot 加载。
3. 有 .env.example。
4. 有 README.md。
5. 有完整目录结构。
6. 有数据库初始化。
7. 有基础群管命令。
8. 有群名片管理。
9. 有群名片锁和定时巡检。
10. 有审计日志。
11. 有权限系统。
12. 有基础测试。
```

