from dataclasses import dataclass
from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent


@dataclass(frozen=True)
class QGuardPermissionCheck:
    checked: bool
    denied_reason: str = ""


def parse_wiki_command(text: str) -> tuple[str, list[str], str] | None:
    stripped = text.strip()
    if stripped.startswith("/知识"):
        rest = stripped.removeprefix("/知识").strip()
        parts = rest.split(maxsplit=1)
        action = parts[0] if parts else "帮助"
        args_text = parts[1] if len(parts) > 1 else ""
        return "/知识", [action], args_text
    for command in ("/问", "/FAQ", "/wiki", "/教程"):
        if stripped == command:
            return command, [], ""
        if stripped.startswith(f"{command} "):
            return command, [], stripped[len(command) :].strip()
    return None


def get_event_group_id(event: MessageEvent) -> int | None:
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        return None
    try:
        return int(group_id)
    except (TypeError, ValueError):
        return None


def is_admin_event(event: MessageEvent) -> bool:
    if int(event.user_id) == 1348984838:
        return True
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", "") if sender is not None else ""
    return role in {"admin", "owner"}


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
        plugin_id="group_wiki",
        selector=selector,
        fallback_role=role,
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
        from nonebot_plugin_qguard.services.auto_recall_service import AUTO_RECALL_CHAT, schedule_auto_recall
    except Exception:
        return
    await schedule_auto_recall(bot, group_id, send_result, message_category=AUTO_RECALL_CHAT)
