from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.message_cache_service import MessageCacheService

message_matcher = on_message(priority=20, block=False)


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
