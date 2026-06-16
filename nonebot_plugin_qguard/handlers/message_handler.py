import asyncio
import time

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.constants import CARD_LOCK_MESSAGE_SCAN_INTERVAL_SECONDS
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.message_cache_service import MessageCacheService

message_matcher = on_message(priority=20, block=False)
_last_group_scan_at: dict[int, float] = {}
_running_group_scans: set[int] = set()


@message_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    try:
        await MessageCacheService().cache_group_message(event)
    except Exception as exc:
        logger.warning("QGuard message cache failed: {}", exc)

    try:
        await CardLockService().repair_member(
            OneBotV11GroupOps(bot),
            event.group_id,
            event.user_id,
            operator_id=None,
            from_event=True,
        )
    except Exception as exc:
        logger.warning("QGuard card-lock check failed: {}", exc)

    _schedule_silent_group_card_scan(bot, event.group_id)


def _schedule_silent_group_card_scan(bot: Bot, group_id: int) -> None:
    now = time.monotonic()
    last_scan_at = _last_group_scan_at.get(group_id, 0.0)
    if group_id in _running_group_scans:
        return
    if now - last_scan_at < CARD_LOCK_MESSAGE_SCAN_INTERVAL_SECONDS:
        return
    _last_group_scan_at[group_id] = now
    _running_group_scans.add(group_id)
    task = asyncio.create_task(_run_silent_group_card_scan(bot, group_id))
    task.add_done_callback(lambda _task: _running_group_scans.discard(group_id))


async def _run_silent_group_card_scan(bot: Bot, group_id: int) -> None:
    try:
        result = await CardLockService().scan_group(
            OneBotV11GroupOps(bot),
            group_id,
            operator_id=None,
            fix=True,
        )
        if result.mismatched or result.fixed or result.failed:
            logger.info(
                "QGuard silent card scan group={} scanned={} mismatched={} fixed={} failed={}",
                group_id,
                result.scanned,
                result.mismatched,
                result.fixed,
                result.failed,
            )
    except Exception as exc:
        logger.warning("QGuard silent card scan failed group={}: {}", group_id, exc)
