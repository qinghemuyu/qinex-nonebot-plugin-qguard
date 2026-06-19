from datetime import datetime

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo
from nonebot_plugin_qguard.services.inactive_cleanup_service import InactiveCleanupService


@scheduler.scheduled_job("cron", hour=4, minute=0, id="qguard_cleanup_message_cache")
async def cleanup_message_cache_job() -> None:
    async with get_session() as session:
        await MessageCacheRepo(session).cleanup_expired()
        await session.commit()


@scheduler.scheduled_job("interval", seconds=60, id="qguard_auto_cleanup_inactive", max_instances=1, coalesce=True)
async def auto_cleanup_inactive_job() -> None:
    bots = [bot for bot in get_bots().values() if isinstance(bot, Bot)]
    if not bots:
        return

    now = datetime.utcnow()
    async with get_session() as session:
        groups = await GroupConfigRepo(session).list_auto_cleanup_due_groups(now)

    service = InactiveCleanupService()
    for config in groups:
        for bot in bots:
            try:
                result = await service.run_group(bot, config.group_id, now=now)
                logger.info(
                    "QGuard auto cleanup group={} checked={} reminded={} kicked={} skipped={} failed={}",
                    config.group_id,
                    result.checked,
                    result.reminded,
                    result.kicked,
                    result.skipped,
                    result.failed,
                )
                break
            except Exception as exc:
                logger.warning("QGuard auto cleanup failed group={} bot={} err={}", config.group_id, bot.self_id, exc)
