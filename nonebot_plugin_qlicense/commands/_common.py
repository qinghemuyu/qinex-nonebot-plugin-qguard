from dataclasses import dataclass
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent

LICENSE_COMMANDS = ("/激活", "/授权")


@dataclass(frozen=True)
class QGuardPermissionCheck:
    checked: bool
    denied_reason: str = ""


def parse_license_command(text: str) -> tuple[str, list[str], str] | None:
    stripped = text.strip()
    for command in LICENSE_COMMANDS:
        if stripped == command:
            return command, [], ""
        if stripped.startswith(f"{command} "):
            rest = stripped[len(command) :].strip()
            parts = rest.split(maxsplit=1)
            action = parts[0] if parts else "帮助"
            args = parts[1] if len(parts) > 1 else ""
            return command, [action], args
    return None


def get_event_group_id(event: MessageEvent) -> int | None:
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        return None
    try:
        return int(group_id)
    except (TypeError, ValueError):
        return None


def extract_at_qq(event: MessageEvent) -> str:
    message = getattr(event, "message", None)
    if message is None:
        return ""
    for segment in message:
        if getattr(segment, "type", "") == "at":
            qq = getattr(segment, "data", {}).get("qq")
            if qq and str(qq).isdigit():
                return str(qq)
    return ""


async def check_qguard_command_permission(
    bot: Bot,
    event: MessageEvent,
    *,
    selector: str,
    fallback_role,
    enforce_plugin_enabled: bool = True,
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

    decision = await RegisteredCommandPermissionService().check(
        OneBotV11GroupOps(bot),
        group_id=group_id,
        operator_id=int(event.user_id),
        plugin_id="qlicense",
        selector=selector,
        fallback_role=QGuardRole(fallback_role),
        enforce_plugin_enabled=enforce_plugin_enabled,
        metadata={"group_id": group_id, "operator_id": int(event.user_id)},
    )
    return QGuardPermissionCheck(True, "" if decision.allowed else decision.reason)


async def send_group_reply(bot: Bot, event: MessageEvent, message: str) -> Any | None:
    group_id = get_event_group_id(event)
    if group_id is None:
        return None
    result = await bot.send_group_msg(group_id=group_id, message=message)
    await schedule_qguard_auto_recall(bot, group_id, result)
    return result


async def finish_reply(matcher: Any, bot: Bot, event: MessageEvent, message: str) -> None:
    if get_event_group_id(event) is None:
        await matcher.finish(message)
    await send_group_reply(bot, event, message)
    await matcher.finish()


async def schedule_qguard_auto_recall(bot: Bot, group_id: int, send_result: Any) -> None:
    try:
        from nonebot_plugin_qguard.services.auto_recall_service import AUTO_RECALL_COMMAND, schedule_auto_recall
    except Exception:
        return
    await schedule_auto_recall(bot, group_id, send_result, message_category=AUTO_RECALL_COMMAND)
