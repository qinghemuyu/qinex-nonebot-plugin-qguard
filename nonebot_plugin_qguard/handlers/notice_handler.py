from typing import Any

from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot, NoticeEvent
from nonebot.log import logger

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.join_welcome_service import JoinWelcomeContext, JoinWelcomeService
from nonebot_plugin_qguard.services.newbie_protection_service import NewbieProtectionService

notice_matcher = on_notice(priority=10, block=False)


def _dump_event(event: NoticeEvent) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump()
    return event.dict()


@notice_matcher.handle()
async def _(bot: Bot, event: NoticeEvent) -> None:
    data = _dump_event(event)
    notice_type = data.get("notice_type")
    sub_type = data.get("sub_type")
    if notice_type == "group_increase":
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        if group_id is None or user_id is None:
            return
        try:
            await NewbieProtectionService().record_join(int(group_id), int(user_id))
        except Exception as exc:
            logger.warning("QGuard newbie join record failed: {}", exc)
        try:
            await JoinWelcomeService().send_welcome_if_enabled(
                OneBotV11GroupOps(bot),
                JoinWelcomeContext(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    sub_type=str(sub_type or ""),
                    operator_id=_int_or_none(data.get("operator_id")),
                    bot_self_id=_int_or_none(getattr(bot, "self_id", None)),
                ),
            )
        except Exception as exc:
            logger.warning("QGuard join welcome failed group={} user={}: {}", group_id, user_id, exc)
        return

    if notice_type not in {"group_card", "group_member_card"} and sub_type != "group_card":
        return
    group_id = data.get("group_id")
    user_id = data.get("user_id")
    if group_id is None or user_id is None:
        return
    current_card = str(data.get("card") or data.get("new_card") or "")
    try:
        await CardLockService().repair_member(
            OneBotV11GroupOps(bot),
            int(group_id),
            int(user_id),
            current_card=current_card,
            from_event=True,
        )
    except Exception as exc:
        logger.warning("QGuard notice card-lock check failed: {}", exc)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
