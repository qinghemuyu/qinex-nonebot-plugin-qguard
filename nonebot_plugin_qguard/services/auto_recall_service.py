import asyncio
from typing import Any

from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo

NON_ADMIN_MAX_AUTO_DELETE_SECONDS = 110


def extract_message_id(send_result: Any) -> int | None:
    if isinstance(send_result, dict):
        message_id = send_result.get("message_id")
    else:
        message_id = getattr(send_result, "message_id", None)

    if message_id is None:
        return None
    try:
        return int(message_id)
    except (TypeError, ValueError):
        return None


def clamp_auto_delete_seconds(seconds: int, role: str | None) -> int:
    if seconds <= 0:
        return 0
    if role not in {"admin", "owner"}:
        return min(seconds, NON_ADMIN_MAX_AUTO_DELETE_SECONDS)
    return seconds


async def get_auto_delete_seconds(bot: Bot, group_id: int) -> int:
    async with get_session() as session:
        config = await GroupConfigRepo(session).get_or_create(group_id)
        seconds = int(config.auto_delete_reply_seconds)
        await session.commit()

    role: str | None = None
    try:
        self_id = int(bot.self_id)
        info = await bot.get_group_member_info(group_id=group_id, user_id=self_id, no_cache=True)
        role = str(info.get("role") or "")
    except Exception as exc:
        logger.warning(f"QGuard 获取机器人群身份失败，将自动撤回时间限制为 110 秒：{exc}")

    return clamp_auto_delete_seconds(seconds, role)


async def schedule_auto_recall(bot: Bot, group_id: int, send_result: Any) -> None:
    message_id = extract_message_id(send_result)
    if message_id is None:
        return

    asyncio.create_task(_recall_when_due(bot, group_id, message_id))


async def _recall_when_due(bot: Bot, group_id: int, message_id: int) -> None:
    try:
        seconds = await get_auto_delete_seconds(bot, group_id)
    except Exception as exc:
        logger.warning(f"QGuard 获取自动撤回配置失败 message_id={message_id}: {exc}")
        return
    if seconds <= 0:
        return

    await asyncio.sleep(seconds)
    try:
        await bot.delete_msg(message_id=message_id)
    except Exception as exc:
        logger.warning(f"QGuard 自动撤回消息失败 message_id={message_id}: {exc}")
