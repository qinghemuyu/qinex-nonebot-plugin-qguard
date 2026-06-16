import asyncio
import time

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.config import load_config
from nonebot_plugin_qguard.constants import CARD_LOCK_MESSAGE_SCAN_INTERVAL_SECONDS
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, RuleAction
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.message_cache_service import MessageCacheService
from nonebot_plugin_qguard.services.newbie_protection_service import NewbieProtectionService
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.punishment_service import PunishmentService
from nonebot_plugin_qguard.services.rule_engine import MessageContext, ModerationDecision, RuleEngine
from nonebot_plugin_qguard.services.score_service import ScoreResult, ScoreService

message_matcher = on_message(priority=20, block=False)
_last_group_scan_at: dict[int, float] = {}
_running_group_scans: set[int] = set()


@message_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    try:
        await MessageCacheService().cache_group_message(event)
    except Exception as exc:
        logger.warning("QGuard message cache failed: {}", exc)

    newbie_handled = False
    try:
        newbie_handled = await NewbieProtectionService().handle_message(OneBotV11GroupOps(bot), _bot_id(bot), event)
    except Exception as exc:
        logger.warning("QGuard newbie protection failed: {}", exc)

    if not newbie_handled:
        try:
            await _run_auto_moderation(bot, event)
        except Exception as exc:
            logger.warning("QGuard auto moderation failed: {}", exc)

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


async def _run_auto_moderation(bot: Bot, event: GroupMessageEvent) -> None:
    plain_text = event.get_plaintext()
    config = load_config()
    if plain_text.strip().startswith(config.qguard_command_prefix):
        return

    image_count = sum(1 for segment in event.message if segment.type == "image")
    at_count = sum(1 for segment in event.message if segment.type == "at")
    link_count = plain_text.count("http://") + plain_text.count("https://")
    decision = await RuleEngine().check(
        MessageContext(
            group_id=event.group_id,
            user_id=event.user_id,
            message_id=event.message_id,
            plain_text=plain_text,
            raw_message=event.message,
            image_count=image_count,
            at_count=at_count,
            link_count=link_count,
        )
    )
    if not decision.hit:
        return

    ops = OneBotV11GroupOps(bot)
    async with get_session() as session:
        protected = await PermissionService(session).is_protected_from_auto_action(ops, event.group_id, event.user_id)
        if protected:
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=_bot_id(bot),
                target_user_id=event.user_id,
                action=AuditAction.HIT_RULE,
                result=AuditResult.SKIPPED,
                reason=decision.reason,
                related_message_id=event.message_id,
                related_rule_id=decision.rule_id,
                metadata={"action": decision.action, "protected": True},
            )
            await session.commit()
            return

    result = await _apply_moderation_decision(ops, _bot_id(bot), event, decision)
    score_result = await ScoreService().apply_decision_score(ops, _bot_id(bot), event, decision)
    async with get_session() as session:
        await AuditLogRepo(session).create(
            group_id=event.group_id,
            operator_id=_bot_id(bot),
            target_user_id=event.user_id,
            action=AuditAction.HIT_RULE,
            result=AuditResult.SUCCESS if result else AuditResult.FAILED,
            reason=decision.reason,
            related_message_id=event.message_id,
            related_rule_id=decision.rule_id,
            metadata={
                "action": decision.action,
                "mute_seconds": decision.mute_seconds,
                "score": _score_metadata(score_result),
            },
        )
        await session.commit()


async def _apply_moderation_decision(
    ops: OneBotV11GroupOps,
    operator_id: int,
    event: GroupMessageEvent,
    decision: ModerationDecision,
) -> bool:
    service = PunishmentService()
    ok = True
    if decision.delete_message:
        delete_result = await service.delete_msg(ops, event.group_id, operator_id, event.message_id, decision.reason)
        ok = ok and delete_result.success

    action = decision.action
    if action == RuleAction.WARN.value:
        result = await service.warn(
            ops,
            event.group_id,
            operator_id,
            event.user_id,
            decision.reason,
            related_message_id=event.message_id,
            score_delta=0,
        )
        ok = ok and result.success
    elif action == RuleAction.MUTE.value:
        result = await service.mute(
            ops,
            event.group_id,
            operator_id,
            event.user_id,
            decision.mute_seconds or 600,
            decision.reason,
            related_message_id=event.message_id,
        )
        ok = ok and result.success
    elif action == RuleAction.KICK.value:
        result = await service.kick(ops, event.group_id, operator_id, event.user_id, decision.reason)
        ok = ok and result.success
    elif action == RuleAction.KICK_BLACK.value:
        result = await service.kick(
            ops,
            event.group_id,
            operator_id,
            event.user_id,
            decision.reason,
            reject_add_request=True,
        )
        ok = ok and result.success
    return ok


def _bot_id(bot: Bot) -> int:
    try:
        return int(bot.self_id)
    except (TypeError, ValueError):
        return 0


def _score_metadata(score_result: ScoreResult) -> dict[str, object]:
    return {
        "delta": score_result.delta,
        "previous_score": score_result.previous_score,
        "current_score": score_result.current_score,
        "penalty_action": score_result.penalty_action,
        "penalty_success": score_result.penalty_success,
    }
