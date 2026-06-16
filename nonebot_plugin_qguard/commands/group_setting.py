from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.group_setting_service import GroupSettingService
from nonebot_plugin_qguard.services.patrol_service import PatrolService
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, make_ops, parse_qguard_args

group_setting_matcher = on_message(priority=5, block=False)


@group_setting_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"群名", "群名锁", "群名修复", "匿名", "匿名锁", "头衔", "巡检"}:
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_OWNER)
    if denied:
        await finish_reply(group_setting_matcher, bot, event, denied)

    ops = make_ops(bot)
    service = GroupSettingService()

    if args[0] == "群名":
        if len(args) < 3 or args[1] != "设置":
            await finish_reply(group_setting_matcher, bot, event, "用法：/管 群名 设置 新群名")
        result = await service.set_group_name(ops, event.group_id, event.user_id, " ".join(args[2:]))
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "群名锁":
        if len(args) >= 2 and args[1] == "关":
            result = await service.unlock_group_name(event.group_id, event.user_id)
            await finish_reply(group_setting_matcher, bot, event, result.message)
        if len(args) < 3 or args[1] != "开":
            await finish_reply(group_setting_matcher, bot, event, "用法：/管 群名锁 开 新群名，或 /管 群名锁 关")
        result = await service.lock_group_name(ops, event.group_id, event.user_id, " ".join(args[2:]))
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "群名修复":
        result = await service.repair_group_name(ops, event.group_id, event.user_id)
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "匿名":
        if len(args) < 2 or args[1] not in {"开", "关"}:
            await finish_reply(group_setting_matcher, bot, event, "用法：/管 匿名 开|关")
        result = await service.set_anonymous(ops, event.group_id, event.user_id, args[1] == "开")
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "匿名锁":
        if len(args) >= 2 and args[1] == "关":
            result = await service.unlock_anonymous(event.group_id, event.user_id)
            await finish_reply(group_setting_matcher, bot, event, result.message)
        if len(args) < 3 or args[1] != "开" or args[2] not in {"开", "关"}:
            await finish_reply(group_setting_matcher, bot, event, "用法：/管 匿名锁 开 开|关，或 /管 匿名锁 关")
        result = await service.lock_anonymous(ops, event.group_id, event.user_id, args[2] == "开")
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "头衔":
        parsed = parse_target(event, args)
        if parsed is None or not parsed.rest:
            await finish_reply(group_setting_matcher, bot, event, "用法：/管 头衔 @用户 头衔")
        result = await service.set_special_title(ops, event.group_id, event.user_id, parsed.user_id, parsed.rest, _bot_id(bot))
        await finish_reply(group_setting_matcher, bot, event, result.message)

    if args[0] == "巡检":
        if len(args) == 1:
            result = await PatrolService().patrol_all(ops, event.group_id, event.user_id)
            await finish_reply(group_setting_matcher, bot, event, result.message)
        if args[1] == "名片":
            result = await PatrolService().patrol_cards(ops, event.group_id, event.user_id)
            await finish_reply(group_setting_matcher, bot, event, result.message)
        if args[1] in {"权限", "群设置"}:
            result = await PatrolService().patrol_group_settings(ops, event.group_id, event.user_id)
            await finish_reply(group_setting_matcher, bot, event, result.message)
        await finish_reply(group_setting_matcher, bot, event, "用法：/管 巡检，/管 巡检 名片，/管 巡检 权限")


def _bot_id(bot: Bot) -> int | None:
    try:
        return int(bot.self_id)
    except (TypeError, ValueError):
        return None
