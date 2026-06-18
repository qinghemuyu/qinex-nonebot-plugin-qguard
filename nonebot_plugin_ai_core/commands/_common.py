from dataclasses import dataclass
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_ai_core.config import Config


@dataclass(frozen=True)
class QGuardPermissionCheck:
    checked: bool
    denied_reason: str = ""


def is_ai_core_admin(event: MessageEvent, config: Config) -> bool:
    return event.user_id in config.ai_core_super_admins


def get_event_group_id(event: MessageEvent) -> int | None:
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        return None
    try:
        return int(group_id)
    except (TypeError, ValueError):
        return None


async def send_group_reply(bot: Bot, event: MessageEvent, message: str) -> Any | None:
    group_id = get_event_group_id(event)
    if group_id is None:
        return None
    result = await bot.send_group_msg(group_id=group_id, message=message)
    await schedule_qguard_auto_recall(bot, group_id, result)
    return result


async def check_qguard_command_permission(
    bot: Bot,
    event: MessageEvent,
    *,
    selector: str,
    fallback_role,
) -> QGuardPermissionCheck:
    group_id = get_event_group_id(event)
    if group_id is None:
        return QGuardPermissionCheck(False)
    try:
        from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
        from nonebot_plugin_qguard.enums import QGuardRole
        from nonebot_plugin_qguard.services.registered_permission_service import RegisteredCommandPermissionService
    except Exception:
        return QGuardPermissionCheck(False)

    role = QGuardRole(fallback_role)
    decision = await RegisteredCommandPermissionService().check(
        OneBotV11GroupOps(bot),
        group_id=group_id,
        operator_id=int(event.user_id),
        plugin_id="ai_core",
        selector=selector,
        fallback_role=role,
        metadata={"group_id": group_id, "operator_id": int(event.user_id)},
    )
    return QGuardPermissionCheck(True, "" if decision.allowed else decision.reason)


async def finish_reply(matcher: Any, bot: Bot, event: MessageEvent, message: str) -> None:
    if get_event_group_id(event) is None:
        await matcher.finish(message)
    await send_group_reply(bot, event, message)
    await matcher.finish()


async def schedule_qguard_auto_recall(bot: Bot, group_id: int, send_result: Any) -> None:
    try:
        from nonebot_plugin_qguard.services.auto_recall_service import AUTO_RECALL_CHAT, schedule_auto_recall
    except Exception:
        return
    await schedule_auto_recall(bot, group_id, send_result, message_category=AUTO_RECALL_CHAT)
