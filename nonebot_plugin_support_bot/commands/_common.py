from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent

SUPPORT_COMMANDS = ("/客服", "/求助", "/不会用", "/售后")
SMART_KEYWORDS = (
    "qinex",
    "QInEX",
    "压枪",
    "连点",
    "投屏",
    "ScreenHub",
    "QInEScreen",
    "P4",
    "S3",
    "ADB",
    "映射没反应",
    "配置不会",
    "鼠标没反应",
    "游戏里没效果",
    "按键没反应",
    "打不开",
    "用不了",
)


def parse_support_command(text: str) -> tuple[str, list[str], str] | None:
    stripped = text.strip()
    for command in SUPPORT_COMMANDS:
        if stripped == command:
            return command, [], ""
        if stripped.startswith(f"{command} "):
            rest = stripped[len(command) :].strip()
            if command == "/客服":
                parts = rest.split(maxsplit=1)
                action = parts[0] if parts else "帮助"
                args = parts[1] if len(parts) > 1 else ""
                return command, [action], args
            return command, [], rest
    return None


def is_smart_candidate(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        return False
    return any(keyword in stripped for keyword in SMART_KEYWORDS)


def get_event_group_id(event: MessageEvent) -> int | None:
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        return None
    try:
        return int(group_id)
    except (TypeError, ValueError):
        return None


def get_reply_text(event: MessageEvent) -> str:
    reply = getattr(event, "reply", None)
    if reply is None:
        return ""
    message = getattr(reply, "message", None)
    if message is None:
        return ""
    if hasattr(message, "extract_plain_text"):
        return str(message.extract_plain_text()).strip()
    if hasattr(message, "get_plaintext"):
        return str(message.get_plaintext()).strip()
    return str(message).strip()


def is_admin_event(event: MessageEvent, admin_ids: list[int]) -> bool:
    if int(event.user_id) in set(admin_ids):
        return True
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", "") if sender is not None else ""
    return role in {"admin", "owner"}


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
