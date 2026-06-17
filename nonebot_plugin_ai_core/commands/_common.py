from typing import Any

from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_ai_core.config import Config


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


async def finish_reply(matcher: Any, bot: Bot, event: MessageEvent, message: str) -> None:
    if get_event_group_id(event) is None:
        await matcher.finish(message)
    await send_group_reply(bot, event, message)
    await matcher.finish()


async def schedule_qguard_auto_recall(bot: Bot, group_id: int, send_result: Any) -> None:
    try:
        from nonebot_plugin_qguard.services.auto_recall_service import schedule_auto_recall
    except Exception:
        return
    await schedule_auto_recall(bot, group_id, send_result)
