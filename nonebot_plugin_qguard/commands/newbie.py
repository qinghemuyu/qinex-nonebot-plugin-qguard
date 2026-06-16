from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, parse_qguard_args

newbie_matcher = on_message(priority=5, block=False)


@newbie_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"新人保护", "新人禁链接", "新人禁图片"}:
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_OWNER)
    if denied:
        await finish_reply(newbie_matcher, bot, event, denied)

    service = GroupConfigService()
    if args[0] in {"新人禁链接", "新人禁图片"}:
        if len(args) < 2 or args[1] not in {"开", "关"}:
            await finish_reply(newbie_matcher, bot, event, f"用法：/管 {args[0]} 开|关")
        if args[0] == "新人禁链接":
            result = await service.set_newbie_block_links(event.group_id, event.user_id, args[1] == "开")
        else:
            result = await service.set_newbie_block_images(event.group_id, event.user_id, args[1] == "开")
        await finish_reply(newbie_matcher, bot, event, result.message)

    if len(args) < 2:
        await finish_reply(newbie_matcher, bot, event, "用法：/管 新人保护 开|关|时长|链接|图片 ...")
    if args[1] in {"开", "关"}:
        result = await service.set_new_member_protection_enabled(event.group_id, event.user_id, args[1] == "开")
        await finish_reply(newbie_matcher, bot, event, result.message)

    if args[1] == "时长":
        if len(args) < 3:
            await finish_reply(newbie_matcher, bot, event, "用法：/管 新人保护 时长 24h")
        try:
            seconds = parse_duration(args[2])
        except ValueError as exc:
            await finish_reply(newbie_matcher, bot, event, str(exc))
        result = await service.set_newbie_protection_seconds(event.group_id, event.user_id, seconds)
        await finish_reply(newbie_matcher, bot, event, result.message)

    if args[1] == "链接":
        if len(args) < 3 or args[2] not in {"开", "关"}:
            await finish_reply(newbie_matcher, bot, event, "用法：/管 新人保护 链接 开|关")
        result = await service.set_newbie_block_links(event.group_id, event.user_id, args[2] == "开")
        await finish_reply(newbie_matcher, bot, event, result.message)

    if args[1] == "图片":
        if len(args) < 3 or args[2] not in {"开", "关"}:
            await finish_reply(newbie_matcher, bot, event, "用法：/管 新人保护 图片 开|关")
        result = await service.set_newbie_block_images(event.group_id, event.user_id, args[2] == "开")
        await finish_reply(newbie_matcher, bot, event, result.message)

    await finish_reply(newbie_matcher, bot, event, "用法：/管 新人保护 开|关|时长|链接|图片 ...")
