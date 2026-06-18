from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.card_service import CardService
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, make_ops, parse_qguard_args

card_matcher = on_message(priority=5, block=False)


@card_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"名片", "清名片", "名片查"}:
        return
    if args[0] == "名片查":
        denied = await ensure_manager(bot, event, QGuardRole.TRUSTED, command_selector="/管 名片查 @用户")
    elif args[0] == "清名片":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN, command_selector="/管 清名片 @用户")
    else:
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN, command_selector="/管 名片 @用户 新名片")
    if denied:
        await finish_reply(card_matcher, bot, event, denied)
    parsed = parse_target(event, args)
    if parsed is None:
        await finish_reply(card_matcher, bot, event, "请指定目标用户，支持 @用户 或 QQ 号。")
    service = CardService()
    ops = make_ops(bot)
    if args[0] == "名片":
        if not parsed.rest:
            await finish_reply(card_matcher, bot, event, "用法：/管 名片 @用户 新名片")
        result = await service.set_card(ops, event.group_id, event.user_id, parsed.user_id, parsed.rest)
        await finish_reply(card_matcher, bot, event, result.message)
    if args[0] == "清名片":
        result = await service.set_card(ops, event.group_id, event.user_id, parsed.user_id, "")
        await finish_reply(card_matcher, bot, event, result.message)
    if args[0] == "名片查":
        result = await service.query_card(ops, event.group_id, parsed.user_id)
        await finish_reply(card_matcher, bot, event, result.message)
