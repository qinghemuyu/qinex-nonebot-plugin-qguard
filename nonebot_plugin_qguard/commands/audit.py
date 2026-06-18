from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import AuditAction, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.utils.message_parser import parse_target
from nonebot_plugin_qguard.utils.formatter import format_audit_logs

from ._common import ensure_manager, finish_reply, parse_qguard_args

audit_matcher = on_message(priority=5, block=False)


@audit_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"日志", "名片日志", "处罚日志"}:
        return
    denied = await ensure_manager(
        bot,
        event,
        QGuardRole.TRUSTED,
        command_selector=_audit_command_selector(args),
    )
    if denied:
        await finish_reply(audit_matcher, bot, event, denied)

    if args[0] == "日志":
        async with get_session() as session:
            if len(args) >= 2 and args[1] == "最近":
                logs = await AuditLogRepo(session).latest(event.group_id, limit=10)
            else:
                parsed = parse_target(event, args, target_index=1)
                if parsed is None:
                    await finish_reply(audit_matcher, bot, event, "用法：/管 日志 最近，或 /管 日志 @用户")
                logs = await AuditLogRepo(session).by_user(event.group_id, parsed.user_id, limit=10)
        await finish_reply(audit_matcher, bot, event, format_audit_logs(logs))

    parsed = parse_target(event, args, target_index=1)
    if parsed is None:
        await finish_reply(audit_matcher, bot, event, f"用法：/管 {args[0]} @用户")
    actions = _card_actions() if args[0] == "名片日志" else _punishment_actions()
    async with get_session() as session:
        logs = await AuditLogRepo(session).by_actions(
            event.group_id,
            actions,
            target_user_id=parsed.user_id,
            limit=10,
        )
    await finish_reply(audit_matcher, bot, event, format_audit_logs(logs))


def _card_actions() -> tuple[AuditAction, ...]:
    return (
        AuditAction.SET_CARD,
        AuditAction.CLEAR_CARD,
        AuditAction.LOCK_CARD,
        AuditAction.UNLOCK_CARD,
        AuditAction.FIX_CARD,
        AuditAction.SCAN_CARD,
    )


def _audit_command_selector(args: list[str]) -> str:
    if args[0] == "日志":
        if len(args) >= 2 and args[1] == "最近":
            return "/管 日志 最近"
        return "/管 日志 @用户"
    if args[0] == "名片日志":
        return "/管 名片日志 @用户"
    return "/管 处罚日志 @用户"


def _punishment_actions() -> tuple[AuditAction, ...]:
    return (
        AuditAction.WARN,
        AuditAction.MUTE,
        AuditAction.UNMUTE,
        AuditAction.KICK,
        AuditAction.KICK_BLACK,
        AuditAction.DELETE_MSG,
        AuditAction.SCORE_PENALTY,
    )
