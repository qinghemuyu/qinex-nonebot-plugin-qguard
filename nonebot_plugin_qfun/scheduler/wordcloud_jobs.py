from datetime import datetime

from nonebot import get_bots
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from nonebot_plugin_qfun.services.wordcloud_service import QFunService


@scheduler.scheduled_job("cron", second=0, id="qfun_daily_wordcloud", max_instances=1, coalesce=True)
async def daily_wordcloud_job() -> None:
    service = QFunService()
    now = datetime.now()
    messages = await service.due_wordcloud_messages(now)
    if not messages:
        return
    bots = list(get_bots().values())
    if not bots:
        return
    for group_id, message in messages:
        sent = False
        for bot in bots:
            try:
                await bot.send_group_msg(group_id=group_id, message=message)
                sent = True
                break
            except Exception as exc:
                logger.warning(f"QFun 每日词云发送失败 group_id={group_id}: {exc}")
        if sent:
            await service.mark_wordcloud_sent(group_id, now)
