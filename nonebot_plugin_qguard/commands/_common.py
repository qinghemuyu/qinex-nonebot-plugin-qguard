from typing import Any

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.config import Config, load_config
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.registered_permission_service import RegisteredCommandPermissionService
from nonebot_plugin_qguard.utils.message_parser import split_command


def get_plugin_config() -> Config:
    return load_config()


def parse_qguard_args(event: GroupMessageEvent) -> list[str]:
    config = get_plugin_config()
    return split_command(config.qguard_command_prefix, event.get_plaintext())


def make_ops(bot: Bot) -> OneBotV11GroupOps:
    return OneBotV11GroupOps(bot)


async def finish_reply(matcher: Any, bot: Bot, event: GroupMessageEvent, message: str) -> None:
    await make_ops(bot).send_group_msg(event.group_id, message)
    await matcher.finish()


async def ensure_manager(
    bot: Bot,
    event: GroupMessageEvent,
    required_role: QGuardRole = QGuardRole.GROUP_ADMIN,
    *,
    command_selector: str | None = None,
    enforce_plugin_enabled: bool = True,
) -> str | None:
    selector = command_selector or _safe_qguard_command_selector(event)
    if selector:
        registered_decision = await RegisteredCommandPermissionService().check(
            make_ops(bot),
            group_id=event.group_id,
            operator_id=event.user_id,
            plugin_id="qguard",
            selector=selector,
            fallback_role=required_role,
            enforce_plugin_enabled=enforce_plugin_enabled,
            metadata={"group_id": event.group_id, "operator_id": event.user_id},
        )
        if not registered_decision.allowed:
            return registered_decision.reason

    async with get_session() as session:
        decision = await PermissionService(session).can_operate(
            make_ops(bot),
            group_id=event.group_id,
            operator_id=event.user_id,
            required_role=required_role,
        )
        if not decision.allowed:
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=event.user_id,
                action=AuditAction.PERMISSION_DENIED,
                result=AuditResult.SKIPPED,
                reason=decision.reason,
                metadata={
                    "required_role": int(required_role),
                    "operator_role": int(decision.operator_role),
                },
            )
            await session.commit()
    return None if decision.allowed else decision.reason


def build_qguard_command_selector(args: list[str]) -> str:
    if not args:
        return ""
    tokens = ["/管", args[0]]
    if args[0] in {"插件"}:
        if len(args) >= 2:
            tokens.append(args[1])
        return " ".join(tokens)

    if args[0] in {"自动撤回", "自动巡检", "规则", "黑名单", "白名单", "新人保护", "名片锁全群", "群名", "群名锁", "匿名", "匿名锁", "巡检"}:
        if len(args) >= 2:
            tokens.append(args[1])
        return " ".join(tokens)

    return " ".join(tokens)


def _safe_qguard_command_selector(event: GroupMessageEvent) -> str:
    if not hasattr(event, "get_plaintext"):
        return ""
    return build_qguard_command_selector(parse_qguard_args(event))
