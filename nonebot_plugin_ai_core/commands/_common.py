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
    return await bot.send_group_msg(group_id=group_id, message=message)


async def finish_reply(matcher: Any, bot: Bot, event: MessageEvent, message: str) -> None:
    if get_event_group_id(event) is None:
        await matcher.finish(message)
    await send_group_reply(bot, event, message)
    await matcher.finish()
