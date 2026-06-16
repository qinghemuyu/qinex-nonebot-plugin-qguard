from nonebot import on_request
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent
from nonebot.log import logger

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.services.join_review_service import JoinReviewService

request_matcher = on_request(priority=5, block=False)


@request_matcher.handle()
async def _(bot: Bot, event: GroupRequestEvent) -> None:
    if event.request_type != "group":
        return

    try:
        result = await JoinReviewService().review_group_request(
            OneBotV11GroupOps(bot),
            group_id=event.group_id,
            user_id=event.user_id,
            flag=event.flag,
            sub_type=event.sub_type,
            comment=event.comment,
            operator_id=_bot_id(bot),
        )
        if result.handled:
            logger.info(
                "QGuard join review group={} user={} approved={} reason={}",
                event.group_id,
                event.user_id,
                result.approved,
                result.reason,
            )
    except Exception as exc:
        logger.warning("QGuard join review failed group={} user={}: {}", event.group_id, event.user_id, exc)


def _bot_id(bot: Bot) -> int:
    try:
        return int(bot.self_id)
    except (TypeError, ValueError):
        return 0
