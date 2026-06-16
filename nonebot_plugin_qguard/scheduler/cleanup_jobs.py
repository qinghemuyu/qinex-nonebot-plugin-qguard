from nonebot_plugin_apscheduler import scheduler

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo


@scheduler.scheduled_job("cron", hour=4, minute=0, id="qguard_cleanup_message_cache")
async def cleanup_message_cache_job() -> None:
    async with get_session() as session:
        await MessageCacheRepo(session).cleanup_expired()
        await session.commit()
