from __future__ import annotations

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, RegistryContext
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService


def _cmd(
    usage: str,
    summary: str,
    role: QGuardRole,
    *,
    danger_level: int = 0,
) -> CommandDescriptor:
    command = usage.split(maxsplit=1)[0]
    return CommandDescriptor(
        command=command,
        summary=summary,
        usage=usage,
        category="qguard",
        required_role=role,
        danger_level=danger_level,
        reply_category="command_reply",
    )


async def _status_provider(context: RegistryContext) -> str:
    if context.group_id is None:
        return "已加载"
    config = await GroupConfigService().status(context.group_id)
    state = "开" if config.enabled else "关"
    auto_recall = "关" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds}s"
    return f"群管 {state}，自动撤回 {auto_recall}"


async def _enabled_provider(context: RegistryContext) -> bool | None:
    if context.group_id is None:
        return None
    config = await GroupConfigService().status(context.group_id)
    return config.enabled


async def _enable_setter(context: RegistryContext, enabled: bool) -> str:
    if context.group_id is None or context.user_id is None:
        return "这个命令只能在群里使用。"
    return (await GroupConfigService().set_enabled(context.group_id, context.user_id, enabled)).message


def get_qguard_descriptor() -> PluginDescriptor:
    commands = (
        _cmd("/管 帮助", "查看统一帮助", QGuardRole.MEMBER),
        _cmd("/管 帮助 全部", "查看全部注册命令", QGuardRole.MEMBER),
        _cmd("/管 状态", "查看本群群管状态", QGuardRole.TRUSTED),
        _cmd("/管 插件", "查看已注册插件", QGuardRole.MEMBER),
        _cmd("/管 插件 状态", "查看插件中心状态", QGuardRole.TRUSTED),
        _cmd("/管 插件 状态 插件ID", "查看单个插件状态", QGuardRole.TRUSTED),
        _cmd("/管 插件 帮助 插件ID", "查看单个插件帮助", QGuardRole.MEMBER),
        _cmd("/管 插件 开 插件ID", "通过插件中心开启插件", QGuardRole.GROUP_OWNER, danger_level=1),
        _cmd("/管 插件 关 插件ID", "通过插件中心关闭插件", QGuardRole.GROUP_OWNER, danger_level=1),
        _cmd("/管 插件 权限 插件ID 命令 角色", "覆盖本群插件命令展示权限", QGuardRole.SUPER_ADMIN, danger_level=2),
        _cmd("/管 开启", "开启本群群管", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 关闭", "关闭本群群管", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 自动撤回 90s", "设置机器人指令回复撤回时间", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 自动撤回 0", "关闭自动撤回", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 自动撤回 分类 指令|聊天|全部|关闭", "设置自动撤回消息分类", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 禁 @用户 10m 原因", "禁言成员", QGuardRole.GROUP_ADMIN, danger_level=2),
        _cmd("/管 解禁 @用户", "解除禁言", QGuardRole.GROUP_ADMIN, danger_level=2),
        _cmd("/管 踢 @用户 原因", "踢出成员", QGuardRole.GROUP_ADMIN, danger_level=3),
        _cmd("/管 踢黑 @用户 原因", "踢出并加入黑名单", QGuardRole.GROUP_OWNER, danger_level=3),
        _cmd("/管 警告 @用户 原因", "警告成员并累计积分", QGuardRole.MINI_ADMIN, danger_level=1),
        _cmd("/管 撤回", "撤回被回复的消息", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 查 @用户", "查询成员信息", QGuardRole.TRUSTED),
        _cmd("/管 积分 @用户", "查询违规积分", QGuardRole.TRUSTED),
        _cmd("/管 积分 清零 @用户", "清零违规积分", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 日志 最近", "查看最近审计日志", QGuardRole.TRUSTED),
        _cmd("/管 日志 @用户", "查看成员审计日志", QGuardRole.TRUSTED),
        _cmd("/管 名片日志 @用户", "查看成员名片日志", QGuardRole.TRUSTED),
        _cmd("/管 处罚日志 @用户", "查看成员处罚日志", QGuardRole.TRUSTED),
        _cmd("/管 最近消息 @用户", "查看成员最近消息缓存", QGuardRole.TRUSTED),
        _cmd("/管 消息 消息ID", "查看缓存消息详情", QGuardRole.TRUSTED),
        _cmd("/管 名片 @用户 新名片", "设置成员群名片", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 清名片 @用户", "清空成员群名片", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 名片查 @用户", "查看成员群名片", QGuardRole.TRUSTED),
        _cmd("/管 名片锁 @用户 固定名片", "锁定成员群名片", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 名片解锁 @用户", "解除成员群名片锁", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 名片锁列表", "查看名片锁列表", QGuardRole.TRUSTED),
        _cmd("/管 名片扫描", "扫描名片锁状态", QGuardRole.GROUP_ADMIN),
        _cmd("/管 名片修复", "修复名片锁不一致成员", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 名片锁全群 开", "开启全群名片锁巡检", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 名片锁全群 关", "关闭全群名片锁巡检", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 规则 添加 关键词 xxx 警告", "添加关键词警告规则", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 规则 添加 关键词 xxx 撤回", "添加关键词撤回规则", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 规则 添加 关键词 xxx 禁言10m", "添加关键词禁言规则", QGuardRole.GROUP_ADMIN, danger_level=2),
        _cmd("/管 规则 添加 正则 xxx 踢出", "添加正则踢出规则", QGuardRole.GROUP_ADMIN, danger_level=3),
        _cmd("/管 规则 删除 ID", "删除规则", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 规则 列表", "查看规则列表", QGuardRole.TRUSTED),
        _cmd("/管 规则 测试 文本", "测试规则命中", QGuardRole.TRUSTED),
        _cmd("/管 广告检测 开", "开启广告检测", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 广告检测 关", "关闭广告检测", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 广告词 添加 xxx", "添加广告词", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 广告词 删除 ID", "删除广告词", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 广告词 列表", "查看广告词列表", QGuardRole.TRUSTED),
        _cmd("/管 刷屏检测 开", "开启刷屏检测", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 刷屏检测 关", "关闭刷屏检测", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 白名单 添加 @用户 原因", "加入白名单", QGuardRole.GROUP_OWNER, danger_level=1),
        _cmd("/管 白名单 删除 @用户", "移出白名单", QGuardRole.GROUP_OWNER, danger_level=1),
        _cmd("/管 白名单 列表", "查看白名单", QGuardRole.GROUP_OWNER),
        _cmd("/管 黑名单 添加 @用户 原因", "加入本群黑名单", QGuardRole.GROUP_ADMIN, danger_level=2),
        _cmd("/管 黑名单 删除 @用户", "移出本群黑名单", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 黑名单 列表", "查看本群黑名单", QGuardRole.GROUP_ADMIN),
        _cmd("/管 黑名单 全局添加 @用户 原因", "加入全局黑名单", QGuardRole.SUPER_ADMIN, danger_level=3),
        _cmd("/管 黑名单 全局删除 @用户", "移出全局黑名单", QGuardRole.SUPER_ADMIN, danger_level=2),
        _cmd("/管 黑名单 全局列表", "查看全局黑名单", QGuardRole.SUPER_ADMIN),
        _cmd("/管 角色 @用户 普通|可信|小管理", "设置插件角色", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 角色查 @用户", "查看插件角色", QGuardRole.GROUP_OWNER),
        _cmd("/管 入群审核 开", "开启入群审核", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 入群审核 关", "关闭入群审核", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 入群暗号 设置 xxx", "设置入群暗号", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 入群拒绝理由 设置 xxx", "设置入群拒绝理由", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人保护 开", "开启新人保护", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人保护 关", "关闭新人保护", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人保护 时长 24h", "设置新人保护时长", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人禁链接 开|关", "设置新人链接限制", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人禁图片 开|关", "设置新人图片限制", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人保护 链接 开|关", "设置新人链接限制", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 新人保护 图片 开|关", "设置新人图片限制", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 群名 设置 新群名", "设置群名", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 群名锁 开 新群名", "开启群名锁", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 群名锁 关", "关闭群名锁", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 群名修复", "修复群名", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 匿名 开|关", "设置匿名聊天", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 匿名锁 开 开|关", "开启匿名锁", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 匿名锁 关", "关闭匿名锁", QGuardRole.GROUP_OWNER, danger_level=2),
        _cmd("/管 全体禁言 开|关", "设置全体禁言", QGuardRole.GROUP_OWNER, danger_level=3),
        _cmd("/管 头衔 @用户 头衔", "设置专属头衔", QGuardRole.GROUP_OWNER, danger_level=1),
        _cmd("/管 巡检", "执行默认巡检", QGuardRole.GROUP_ADMIN),
        _cmd("/管 巡检 名片", "执行名片巡检", QGuardRole.GROUP_ADMIN),
        _cmd("/管 巡检 权限", "执行权限巡检", QGuardRole.GROUP_ADMIN),
        _cmd("/管 自动巡检 开", "开启自动巡检", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 自动巡检 关", "关闭自动巡检", QGuardRole.GROUP_ADMIN, danger_level=1),
        _cmd("/管 自动巡检 间隔 5s", "设置自动巡检间隔", QGuardRole.GROUP_ADMIN, danger_level=1),
    )
    return PluginDescriptor(
        plugin_id="qguard",
        display_name="QGuard 群管",
        module_name="nonebot_plugin_qguard",
        description="群管、权限、审核、名片锁、自动撤回和插件中心控制平面。",
        commands=commands,
        default_enabled=True,
        status_provider=_status_provider,
        group_enabled_provider=_enabled_provider,
        group_enable_setter=_enable_setter,
    )
