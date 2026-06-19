from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.constants import DEFAULT_REASON
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.bulk_recall_service import BulkRecallService
from nonebot_plugin_qguard.services.punishment_service import PunishmentService
from nonebot_plugin_qguard.utils.message_parser import get_reply_message_id, parse_target
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, make_ops, parse_qguard_args

punish_matcher = on_message(priority=5, block=False)


@punish_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"禁", "解禁", "踢", "踢黑", "警告", "撤回", "查"}:
        return
    denied = await ensure_manager(
        bot,
        event,
        _required_role(args[0]),
        command_selector=_command_selector(args),
    )
    if denied:
        await finish_reply(punish_matcher, bot, event, denied)
    ops = make_ops(bot)
    service = PunishmentService()

    if args[0] == "撤回":
        if len(args) >= 2:
            try:
                count = int(args[1])
            except ValueError:
                await finish_reply(punish_matcher, bot, event, "用法：/管 撤回 100，或回复消息后发送 /管 撤回。")
            result = await BulkRecallService().recall_recent(
                ops,
                group_id=event.group_id,
                operator_id=event.user_id,
                command_message_id=event.message_id,
                count=count,
            )
            await finish_reply(punish_matcher, bot, event, result.message)
        message_id = get_reply_message_id(event)
        if message_id is None:
            await finish_reply(punish_matcher, bot, event, "请回复需要撤回的消息后再发送 /管 撤回。")
        result = await service.delete_msg(ops, event.group_id, event.user_id, message_id, "人工撤回")
        await finish_reply(punish_matcher, bot, event, result.message)

    parsed = parse_target(event, args)
    if parsed is None:
        await finish_reply(punish_matcher, bot, event, "请指定目标用户，支持 @用户 或 QQ 号。")

    if args[0] == "查":
        try:
            info = await ops.get_group_member_info(event.group_id, parsed.user_id)
        except Exception as exc:
            await finish_reply(punish_matcher, bot, event, f"查询失败：{exc}")
        await finish_reply(
            punish_matcher,
            bot,
            event,
            f"用户：{parsed.user_id}\n"
            f"昵称：{info.get('nickname', '')}\n"
            f"名片：{info.get('card') or '空'}\n"
            f"角色：{info.get('role', 'member')}"
        )

    reason = parsed.rest or DEFAULT_REASON
    if args[0] == "禁":
        parts = parsed.rest.split(maxsplit=1)
        if not parts:
            await finish_reply(punish_matcher, bot, event, "用法：/管 禁 @用户 10m 原因")
        try:
            seconds = parse_duration(parts[0])
        except ValueError as exc:
            await finish_reply(punish_matcher, bot, event, str(exc))
        reason = parts[1] if len(parts) > 1 else DEFAULT_REASON
        result = await service.mute(ops, event.group_id, event.user_id, parsed.user_id, seconds, reason)
        await finish_reply(punish_matcher, bot, event, result.message)
    if args[0] == "解禁":
        result = await service.unmute(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await finish_reply(punish_matcher, bot, event, result.message)
    if args[0] == "踢":
        result = await service.kick(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await finish_reply(punish_matcher, bot, event, result.message)
    if args[0] == "踢黑":
        result = await service.kick(ops, event.group_id, event.user_id, parsed.user_id, reason, reject_add_request=True)
        await finish_reply(punish_matcher, bot, event, result.message)
    if args[0] == "警告":
        result = await service.warn(ops, event.group_id, event.user_id, parsed.user_id, reason)
        await finish_reply(punish_matcher, bot, event, result.message)


def _required_role(action: str) -> QGuardRole:
    if action in {"禁", "解禁", "警告", "撤回"}:
        return QGuardRole.MINI_ADMIN
    if action == "查":
        return QGuardRole.TRUSTED
    if action == "踢黑":
        return QGuardRole.GROUP_OWNER
    return QGuardRole.GROUP_ADMIN


def _command_selector(args: list[str]) -> str:
    action = args[0]
    if action == "撤回" and len(args) >= 2 and args[1].isdigit():
        return "/管 撤回 数量"
    selectors = {
        "禁": "/管 禁 @用户 10m 原因",
        "解禁": "/管 解禁 @用户",
        "踢": "/管 踢 @用户 原因",
        "踢黑": "/管 踢黑 @用户 原因",
        "警告": "/管 警告 @用户 原因",
        "撤回": "/管 撤回",
        "查": "/管 查 @用户",
    }
    return selectors[action]
