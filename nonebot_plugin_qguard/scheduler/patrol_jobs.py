from datetime import datetime

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.patrol_service import PatrolService


@scheduler.scheduled_job("interval", seconds=5, id="qguard_auto_patrol", max_instances=1, coalesce=True)
async def auto_patrol_job() -> None:
    bots = [bot for bot in get_bots().values() if isinstance(bot, Bot)]
    if not bots:
        return

    now = datetime.utcnow()
    async with get_session() as session:
        groups = await GroupConfigRepo(session).list_auto_patrol_due_groups(now)

    for config in groups:
        attempted = False
        for bot in bots:
            attempted = True
            try:
                result = await PatrolService().patrol_all(OneBotV11GroupOps(bot), config.group_id, operator_id=None)
                logger.info(
                    "QGuard auto patrol group={} checked={} fixed={} failed={}",
                    config.group_id,
                    result.checked,
                    result.fixed,
                    result.failed,
                )
                break
            except Exception as exc:
                logger.warning("QGuard auto patrol failed group={} bot={} err={}", config.group_id, bot.self_id, exc)

        if attempted:
            async with get_session() as session:
                await GroupConfigRepo(session).mark_auto_patrol_ran(config.group_id, now)
                await session.commit()
