from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.message_cache_service import MessageCacheService
from nonebot_plugin_qguard.utils.formatter import format_cached_messages
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, parse_qguard_args

message_query_matcher = on_message(priority=5, block=False)


@message_query_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "最近消息":
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(message_query_matcher, bot, event, denied)

    parsed = parse_target(event, args)
    if parsed is None:
        await finish_reply(message_query_matcher, bot, event, "用法：/管 最近消息 @用户")
    messages = await MessageCacheService().latest_by_user(event.group_id, parsed.user_id, limit=10)
    await finish_reply(message_query_matcher, bot, event, format_cached_messages(messages))
