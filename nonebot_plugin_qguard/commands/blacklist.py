from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.moderation_list_service import ModerationListService
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, parse_qguard_args

blacklist_matcher = on_message(priority=5, block=False)


@blacklist_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "黑名单":
        return

    if len(args) < 2 or args[1] not in {"添加", "加入", "删除", "移除", "列表", "全局添加", "全局加入", "全局删除", "全局移除", "全局列表"}:
        await finish_reply(blacklist_matcher, bot, event, "用法：/管 黑名单 添加|删除|列表 ...")

    is_global_action = args[1].startswith("全局")
    denied = await ensure_manager(bot, event, QGuardRole.SUPER_ADMIN if is_global_action else QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(blacklist_matcher, bot, event, denied)

    service = ModerationListService()
    action = args[1]

    if action == "全局列表":
        items = await service.list_global_blacklist()
        if not items:
            await finish_reply(blacklist_matcher, bot, event, "当前全局黑名单为空。")
        await finish_reply(blacklist_matcher, bot, event, _format_items("全局黑名单", items))

    if action == "列表":
        items = await service.list_blacklist(event.group_id)
        if not items:
            await finish_reply(blacklist_matcher, bot, event, "当前黑名单为空。")
        await finish_reply(blacklist_matcher, bot, event, _format_items("黑名单", items))

    parsed = parse_target(event, args, target_index=2)
    if parsed is None:
        await finish_reply(blacklist_matcher, bot, event, "请指定目标用户，支持 @用户 或 QQ 号。")

    if action in {"添加", "加入", "全局添加", "全局加入"}:
        result = await service.add_blacklist(
            None if is_global_action else event.group_id,
            event.user_id,
            parsed.user_id,
            parsed.rest or None,
        )
        await finish_reply(blacklist_matcher, bot, event, result.message)

    result = await service.remove_blacklist(None if is_global_action else event.group_id, event.user_id, parsed.user_id)
    await finish_reply(blacklist_matcher, bot, event, result.message)


def _format_items(title: str, items: list[tuple[int, str]]) -> str:
    lines = [f"{title}："]
    for user_id, reason in items:
        suffix = f" - {reason}" if reason else ""
        lines.append(f"{user_id}{suffix}")
    return "\n".join(lines)
