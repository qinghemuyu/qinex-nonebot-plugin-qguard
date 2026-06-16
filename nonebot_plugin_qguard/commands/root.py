from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.utils.formatter import format_group_status

from ._common import ensure_manager, parse_qguard_args

root_matcher = on_message(priority=5, block=False)

HELP_TEXT = """QGuard 命令
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
/管 名片修复"""


@root_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"帮助", "状态", "开启", "关闭"}:
        return
    service = GroupConfigService()
    if args[0] == "帮助":
        await root_matcher.finish(HELP_TEXT)
    if args[0] == "状态":
        config = await service.status(event.group_id)
        await root_matcher.finish(format_group_status(config))
    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await root_matcher.finish(denied)
    if args[0] == "开启":
        result = await service.set_enabled(event.group_id, event.user_id, True)
        await root_matcher.finish(result.message)
    if args[0] == "关闭":
        result = await service.set_enabled(event.group_id, event.user_id, False)
        await root_matcher.finish(result.message)
