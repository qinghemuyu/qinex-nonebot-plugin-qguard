from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.inactive_cleanup_service import (
    InactiveCleanupService,
    deserialize_cleanup_reminder_days,
    format_cleanup_reminder_days,
    parse_cleanup_day_token,
)
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, parse_qguard_args

cleanup_matcher = on_message(priority=5, block=False)


@cleanup_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "自动清理":
        return

    denied = await ensure_manager(
        bot,
        event,
        QGuardRole.GROUP_ADMIN,
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
        result = await service.run_group(bot, event.group_id, operator_id=event.user_id)
        await finish_reply(cleanup_matcher, bot, event, result.message)

    await finish_reply(
        cleanup_matcher,
        bot,
        event,
        "用法：/管 自动清理 状态|开|关|提醒 30d 60d|踢出 90d|间隔 1d|执行",
    )


def _command_selector(args: list[str]) -> str:
    if len(args) >= 2:
        return f"/管 自动清理 {args[1]}"
    return "/管 自动清理 状态"
