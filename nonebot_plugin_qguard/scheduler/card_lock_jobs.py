from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.models.base import plugin_config, get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.card_lock_service import CardLockService


@scheduler.scheduled_job(
    "interval",
    seconds=plugin_config.qguard_card_lock_patrol_interval_seconds,
    id="qguard_card_lock_patrol",
)
async def card_lock_patrol_job() -> None:
    bots = [bot for bot in get_bots().values() if isinstance(bot, Bot)]
    if not bots:
        return
    async with get_session() as session:
        groups = await GroupConfigRepo(session).list_card_lock_enabled_groups()
    for config in groups:
        for bot in bots:
            try:
                result = await CardLockService().scan_group(OneBotV11GroupOps(bot), config.group_id, fix=True)
                logger.info(
                    "QGuard card patrol group={} scanned={} mismatched={} fixed={} failed={}",
                    config.group_id,
                    result.scanned,
                    result.mismatched,
                    result.fixed,
                    result.failed,
                )
                break
            except Exception as exc:
                logger.warning("QGuard card patrol failed group={} bot={} err={}", config.group_id, bot.self_id, exc)
