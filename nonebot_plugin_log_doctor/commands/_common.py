from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent


LOG_DOCTOR_COMMANDS = ("/诊断", "/报错", "/看日志", "/logdoctor")


def parse_log_doctor_command(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    for command in LOG_DOCTOR_COMMANDS:
        if stripped == command:
            return command, ""
        if stripped.startswith(f"{command} "):
            return command, stripped[len(command) :].strip()
    return None


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
