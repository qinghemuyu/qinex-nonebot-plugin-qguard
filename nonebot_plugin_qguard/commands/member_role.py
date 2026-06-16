from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.member_role_service import ROLE_LABELS, MemberRoleService, parse_plugin_role
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, parse_qguard_args

member_role_matcher = on_message(priority=5, block=False)


@member_role_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"角色", "角色查"}:
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_OWNER)
    if denied:
        await finish_reply(member_role_matcher, bot, event, denied)

    service = MemberRoleService()
    if args[0] == "角色查":
        parsed = parse_target(event, args)
        if parsed is None:
            await finish_reply(member_role_matcher, bot, event, "用法：/管 角色查 @用户")
        role = await service.get_plugin_role(event.group_id, parsed.user_id)
        await finish_reply(member_role_matcher, bot, event, f"{parsed.user_id} 插件角色：{ROLE_LABELS[role]}")

    parsed = parse_target(event, args)
    if parsed is None or not parsed.rest:
        await finish_reply(member_role_matcher, bot, event, "用法：/管 角色 @用户 普通|可信|小管理")
    try:
        role = parse_plugin_role(parsed.rest)
    except ValueError as exc:
        await finish_reply(member_role_matcher, bot, event, str(exc))
    result = await service.set_role(event.group_id, event.user_id, parsed.user_id, role)
    await finish_reply(member_role_matcher, bot, event, result.message)
