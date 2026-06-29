import re

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.inactive_cleanup_service import (
    InactiveCleanupService,
    PendingCleanupMember,
    deserialize_cleanup_reminder_days,
    format_cleanup_reminder_days,
    parse_cleanup_day_token,
)
from nonebot_plugin_qguard.utils.message_parser import get_at_user_ids
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, parse_qguard_args

cleanup_matcher = on_message(priority=5, block=False)

_USER_ID_RE = re.compile(r"\d{5,12}")
_EXCLUDE_TOKENS = {"排除", "保留", "跳过", "不踢", "忽略"}


@cleanup_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "自动清理":
        return

    denied = await ensure_manager(
        bot,
        event,
        _required_role(args),
        command_selector=_command_selector(args),
    )
    if denied:
        await finish_reply(cleanup_matcher, bot, event, denied)

    service = InactiveCleanupService()
    if len(args) == 1 or args[1] == "状态":
        config = await service.status(event.group_id)
        reminders = format_cleanup_reminder_days(
            deserialize_cleanup_reminder_days(config.auto_cleanup_reminder_days)
        )
        last_run = config.last_auto_cleanup_at or "暂无"
        await finish_reply(
            cleanup_matcher,
            bot,
            event,
            "自动清理状态\n"
            f"开关：{'开' if config.auto_cleanup_enabled else '关'}\n"
            f"提醒档位：{reminders}\n"
            f"踢出阈值：{config.auto_cleanup_kick_days}天\n"
            "踢出确认：主人确认后执行\n"
            f"扫描间隔：{config.auto_cleanup_interval_seconds}秒\n"
            f"上次扫描：{last_run}",
        )

    action = args[1]
    if action in {"开", "开启"}:
        result = await service.set_enabled(event.group_id, event.user_id, True)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"关", "关闭"}:
        result = await service.set_enabled(event.group_id, event.user_id, False)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"提醒", "提醒档位"}:
        if len(args) < 3:
            await finish_reply(cleanup_matcher, bot, event, "用法：/管 自动清理 提醒 30d 60d，关闭提醒用 /管 自动清理 提醒 关")
        if args[2] in {"关", "关闭", "0"}:
            days: list[int] = []
        else:
            try:
                days = [parse_cleanup_day_token(item) for item in args[2:]]
            except ValueError as exc:
                await finish_reply(cleanup_matcher, bot, event, str(exc))
        result = await service.set_reminder_days(event.group_id, event.user_id, days)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"踢出", "踢", "清理"}:
        if len(args) < 3:
            await finish_reply(cleanup_matcher, bot, event, "用法：/管 自动清理 踢出 90d")
        try:
            days = parse_cleanup_day_token(args[2])
        except ValueError as exc:
            await finish_reply(cleanup_matcher, bot, event, str(exc))
        result = await service.set_kick_days(event.group_id, event.user_id, days)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"间隔", "扫描间隔"}:
        if len(args) < 3:
            await finish_reply(cleanup_matcher, bot, event, "用法：/管 自动清理 间隔 1d")
        try:
            seconds = parse_duration(args[2])
        except ValueError as exc:
            await finish_reply(cleanup_matcher, bot, event, str(exc))
        result = await service.set_interval_seconds(event.group_id, event.user_id, seconds)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"执行", "扫描", "立即"}:
        result = await service.run_group(bot, event.group_id, operator_id=event.user_id, notify_owners=False)
        await finish_reply(cleanup_matcher, bot, event, result.message)
    if action in {"待确认", "预览", "清单", "列表"}:
        pending = await service.list_pending(event.group_id, limit=50)
        await finish_reply(cleanup_matcher, bot, event, _format_pending_members(pending))
    if action in {"确认", "确认清理"}:
        exclude_user_ids, _ = _parse_user_ids_and_rest(event, args, 2)
        result = await service.confirm_pending(
            bot,
            event.group_id,
            operator_id=event.user_id,
            exclude_user_ids=exclude_user_ids,
        )
        suffix = ""
        if exclude_user_ids:
            suffix = "\n已排除并加入保留名单：" + "、".join(str(user_id) for user_id in exclude_user_ids)
        await finish_reply(cleanup_matcher, bot, event, result.message + suffix)
    if action in {"保留", "排除", "跳过"}:
        user_ids, reason = _parse_user_ids_and_rest(event, args, 2)
        if not user_ids:
            await finish_reply(cleanup_matcher, bot, event, "用法：/管 自动清理 保留 QQ 原因")
        result = await service.keep_members(
            event.group_id,
            event.user_id,
            user_ids,
            reason=reason or "自动清理保留",
        )
        await finish_reply(
            cleanup_matcher,
            bot,
            event,
            "已加入自动清理保留名单："
            + "、".join(str(user_id) for user_id in user_ids)
            + f"\n已清除待确认记录：{result.cleared} 条。",
        )
    if action in {"取消", "撤销"}:
        user_ids, _ = _parse_user_ids_and_rest(event, args, 2)
        result = await service.cancel_pending(event.group_id, event.user_id, user_ids or None)
        await finish_reply(cleanup_matcher, bot, event, result.message)

    await finish_reply(
        cleanup_matcher,
        bot,
        event,
        "用法：/管 自动清理 状态|开|关|提醒 30d 60d|踢出 90d|间隔 1d|执行|待确认|确认|保留 QQ 原因|取消",
    )


def _required_role(args: list[str]) -> QGuardRole:
    if len(args) < 2:
        return QGuardRole.GROUP_ADMIN
    action = args[1]
    if action in {"确认", "确认清理"}:
        return QGuardRole.SUPER_ADMIN
    if action in {"保留", "排除", "跳过", "取消", "撤销"}:
        return QGuardRole.GROUP_OWNER
    return QGuardRole.GROUP_ADMIN


def _command_selector(args: list[str]) -> str:
    if len(args) >= 2:
        return f"/管 自动清理 {args[1]}"
    return "/管 自动清理 状态"


def _parse_user_ids_and_rest(event: GroupMessageEvent, args: list[str], start_index: int) -> tuple[list[int], str]:
    user_ids = set(get_at_user_ids(event.message))
    rest: list[str] = []
    for token in args[start_index:]:
        if token in _EXCLUDE_TOKENS:
            continue
        matches = _USER_ID_RE.findall(token)
        if matches:
            user_ids.update(int(match) for match in matches)
            continue
        if "[CQ:at" in token:
            continue
        rest.append(token)
    return sorted(user_ids), " ".join(rest).strip()


def _format_pending_members(items: list[PendingCleanupMember]) -> str:
    if not items:
        return "当前没有自动清理待确认成员。"

    lines = [
        "自动清理待确认",
        "确认踢出：/管 自动清理 确认",
        "排除成员：/管 自动清理 确认 排除 QQ",
        "长期保留：/管 自动清理 保留 QQ 原因",
        "",
    ]
    for index, item in enumerate(items, start=1):
        pending_at = item.pending_at.strftime("%m-%d %H:%M") if item.pending_at else "未知"
        lines.append(f"{index}. {item.user_id}，未发言 {item.inactive_days} 天，进入待确认 {pending_at}")
    if len(items) >= 50:
        lines.append("只显示前 50 条。")
    return "\n".join(lines)
