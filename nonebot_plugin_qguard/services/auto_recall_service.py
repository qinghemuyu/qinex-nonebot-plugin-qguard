import asyncio
import re
from typing import Any

from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo

NON_ADMIN_MAX_AUTO_DELETE_SECONDS = 110
AUTO_RECALL_COMMAND = "command"
AUTO_RECALL_CHAT = "chat"
AUTO_RECALL_ALL = {AUTO_RECALL_COMMAND, AUTO_RECALL_CHAT}


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


def parse_auto_recall_categories(text: str) -> set[str]:
    normalized = text.strip().lower()
    if normalized in {"全部", "所有", "all", "*"}:
        return set(AUTO_RECALL_ALL)
    if normalized in {"关闭", "关", "无", "none", "off", "0"}:
        return set()

    categories: set[str] = set()
    for item in re.split(r"[\s,，、|/+]+", normalized):
        if not item:
            continue
        if item in {"指令", "命令", "command", "cmd"}:
            categories.add(AUTO_RECALL_COMMAND)
        elif item in {"聊天", "对话", "ai", "chat"}:
            categories.add(AUTO_RECALL_CHAT)
        else:
            raise ValueError("分类只支持：指令、聊天、全部、关闭。")
    return categories


def serialize_auto_recall_categories(categories: set[str]) -> str:
    ordered = [item for item in (AUTO_RECALL_COMMAND, AUTO_RECALL_CHAT) if item in categories]
    return ",".join(ordered)


def deserialize_auto_recall_categories(raw: str | None) -> set[str]:
    if not raw:
        return set()
    try:
        return parse_auto_recall_categories(raw)
    except ValueError:
        return {item for item in raw.split(",") if item in AUTO_RECALL_ALL}


def format_auto_recall_categories(categories: set[str]) -> str:
    if categories == AUTO_RECALL_ALL:
        return "全部"
    if not categories:
        return "关闭"
    labels = []
    if AUTO_RECALL_COMMAND in categories:
        labels.append("指令")
    if AUTO_RECALL_CHAT in categories:
        labels.append("聊天")
    return "、".join(labels)


def should_auto_recall_message(configured_categories: str | None, message_category: str) -> bool:
    return message_category in deserialize_auto_recall_categories(configured_categories)


async def get_auto_delete_seconds(bot: Bot, group_id: int, message_category: str = AUTO_RECALL_COMMAND) -> int:
    async with get_session() as session:
        config = await GroupConfigRepo(session).get_or_create(group_id)
        seconds = int(config.auto_delete_reply_seconds)
        categories = config.auto_delete_reply_categories
        await session.commit()

    if not should_auto_recall_message(categories, message_category):
        return 0

    role: str | None = None
    try:
        self_id = int(bot.self_id)
        info = await bot.get_group_member_info(group_id=group_id, user_id=self_id, no_cache=True)
        role = str(info.get("role") or "")
    except Exception as exc:
        logger.warning(f"QGuard 获取机器人群身份失败，将自动撤回时间限制为 110 秒：{exc}")

    return clamp_auto_delete_seconds(seconds, role)


async def schedule_auto_recall(
    bot: Bot,
    group_id: int,
    send_result: Any,
    message_category: str = AUTO_RECALL_COMMAND,
) -> None:
    message_id = extract_message_id(send_result)
    if message_id is None:
        return

    asyncio.create_task(_recall_when_due(bot, group_id, message_id, message_category))


async def _recall_when_due(bot: Bot, group_id: int, message_id: int, message_category: str) -> None:
    try:
        seconds = await get_auto_delete_seconds(bot, group_id, message_category)
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
