from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.utils.formatter import format_group_status
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, parse_qguard_args

root_matcher = on_message(priority=5, block=False)

HELP_TEXT = """QGuard 命令
/管 帮助
/管 状态
/管 开启
/管 关闭
/管 自动撤回 90s
/管 自动撤回 0
/管 禁 @用户 10m 原因
/管 解禁 @用户
/管 踢 @用户 原因
/管 踢黑 @用户 原因
/管 警告 @用户 原因
/管 撤回
/管 查 @用户
/管 积分 @用户
/管 积分 清零 @用户
/管 日志 最近
/管 日志 @用户
/管 名片日志 @用户
/管 处罚日志 @用户
/管 最近消息 @用户
/管 名片 @用户 新名片
/管 清名片 @用户
/管 名片查 @用户
/管 名片锁 @用户 固定名片
/管 名片解锁 @用户
/管 名片锁列表
/管 名片扫描
/管 名片修复
/管 规则 添加 关键词 xxx 警告
/管 规则 添加 关键词 xxx 撤回
/管 规则 添加 关键词 xxx 禁言10m
/管 规则 添加 正则 xxx 踢出
/管 规则 删除 ID
/管 规则 列表
/管 规则 测试 文本
/管 广告检测 开
/管 广告检测 关
/管 广告词 添加 xxx
/管 广告词 删除 ID
/管 广告词 列表
/管 刷屏检测 开
/管 刷屏检测 关
/管 白名单 添加 @用户 原因
/管 白名单 删除 @用户
/管 白名单 列表
/管 黑名单 添加 @用户 原因
/管 黑名单 删除 @用户
/管 黑名单 列表
/管 黑名单 全局添加 @用户 原因
/管 黑名单 全局删除 @用户
/管 黑名单 全局列表
/管 角色 @用户 普通|可信|小管理
/管 角色查 @用户
/管 入群审核 开
/管 入群审核 关
/管 入群暗号 设置 xxx
/管 入群拒绝理由 设置 xxx
/管 新人保护 开
/管 新人保护 关
/管 新人保护 时长 24h
/管 新人禁链接 开|关
/管 新人禁图片 开|关
/管 新人保护 链接 开|关
/管 新人保护 图片 开|关
/管 群名 设置 新群名
/管 群名锁 开 新群名
/管 群名锁 关
/管 群名修复
/管 匿名 开|关
/管 匿名锁 开 开|关
/管 匿名锁 关
/管 全体禁言 开|关
/管 头衔 @用户 头衔
/管 巡检
/管 巡检 名片
/管 巡检 权限
/管 自动巡检 开
/管 自动巡检 关
/管 自动巡检 间隔 5s"""


@root_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"帮助", "状态", "开启", "关闭", "自动撤回"}:
        return
    service = GroupConfigService()
    if args[0] == "帮助":
        await finish_reply(root_matcher, bot, event, HELP_TEXT)
    if args[0] == "状态":
        config = await service.status(event.group_id)
        await finish_reply(root_matcher, bot, event, format_group_status(config))
    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(root_matcher, bot, event, denied)
    if args[0] == "开启":
        result = await service.set_enabled(event.group_id, event.user_id, True)
        await finish_reply(root_matcher, bot, event, result.message)
    if args[0] == "关闭":
        result = await service.set_enabled(event.group_id, event.user_id, False)
        await finish_reply(root_matcher, bot, event, result.message)
    if args[0] == "自动撤回":
        if len(args) < 2:
            config = await service.status(event.group_id)
            current = "关闭" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds} 秒"
            await finish_reply(root_matcher, bot, event, f"当前自动撤回：{current}。\n用法：/管 自动撤回 90s，关闭用 /管 自动撤回 0")
        try:
            seconds = parse_duration(args[1])
        except ValueError as exc:
            await finish_reply(root_matcher, bot, event, str(exc))
        result = await service.set_auto_delete_reply_seconds(event.group_id, event.user_id, seconds)
        await finish_reply(root_matcher, bot, event, result.message)
