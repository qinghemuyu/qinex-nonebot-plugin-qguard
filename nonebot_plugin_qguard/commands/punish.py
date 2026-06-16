from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.constants import DEFAULT_REASON
from nonebot_plugin_qguard.services.punishment_service import PunishmentService
from nonebot_plugin_qguard.utils.message_parser import get_reply_message_id, parse_target
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import make_ops, parse_qguard_args

punish_matcher = on_message(priority=5, block=False)


@punish_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"禁", "解禁", "踢", "踢黑", "警告", "撤回", "查"}:
        return
    ops = make_ops(bot)
    service = PunishmentService()

    if args[0] == "撤回":
        message_id = get_reply_message_id(event)
        if message_id is None:
            await punish_matcher.finish("请回复需要撤回的消息后再发送 /管 撤回。")
        result = await service.delete_msg(ops, event.group_id, event.user_id, message_id, "人工撤回")
        await punish_matcher.finish(result.message)

    parsed = parse_target(event, args)
    if parsed is None:
        await punish_matcher.finish("请指定目标用户，支持 @用户 或 QQ 号。")

    if args[0] == "查":
        try:
            info = await ops.get_group_member_info(event.group_id, parsed.user_id)
        except Exception as exc:
            await punish_matcher.finish(f"查询失败：{exc}")
        await punish_matcher.finish(
            f"用户：{parsed.user_id}\n"
            f"昵称：{info.get('nickname', '')}\n"
            f"名片：{info.get('card') or '空'}\n"
            f"角色：{info.get('role', 'member')}"
        )

    reason = parsed.rest or DEFAULT_REASON
    if args[0] == "禁":
        parts = parsed.rest.split(maxsplit=1)
        if not parts:
            await punish_matcher.finish("用法：/管 禁 @用户 10m 原因")
        try:
            seconds = parse_duration(parts[0])
        except ValueError as exc:
            await punish_matcher.finish(str(exc))
        reason = parts[1] if len(parts) > 1 else DEFAULT_REASON
        result = await service.mute(ops, event.group_id, event.user_id, parsed.user_id, seconds, reason)
        await punish_matcher.finish(result.message)
    if args[0] == "解禁":
        result = await service.unmute(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await punish_matcher.finish(result.message)
    if args[0] == "踢":
        result = await service.kick(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await punish_matcher.finish(result.message)
    if args[0] == "踢黑":
        result = await service.kick(ops, event.group_id, event.user_id, parsed.user_id, reason, reject_add_request=True)
        await punish_matcher.finish(result.message)
    if args[0] == "警告":
        result = await service.warn(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await punish_matcher.finish(result.message)
