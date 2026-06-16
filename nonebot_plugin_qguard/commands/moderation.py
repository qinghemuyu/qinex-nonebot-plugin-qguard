from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService

from ._common import ensure_manager, finish_reply, parse_qguard_args

moderation_matcher = on_message(priority=5, block=False)


@moderation_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"广告检测", "刷屏检测"}:
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(moderation_matcher, bot, event, denied)

    if len(args) < 2 or args[1] not in {"开", "关"}:
        await finish_reply(moderation_matcher, bot, event, f"用法：/管 {args[0]} 开|关")

    service = GroupConfigService()
    enabled = args[1] == "开"
    if args[0] == "广告检测":
        result = await service.set_anti_ad_enabled(event.group_id, event.user_id, enabled)
    else:
        result = await service.set_anti_spam_enabled(event.group_id, event.user_id, enabled)
    await finish_reply(moderation_matcher, bot, event, result.message)
