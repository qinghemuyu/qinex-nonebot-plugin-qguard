from dataclasses import dataclass

from pydantic import BaseModel

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.constants import (
    SCORE_KICK_THRESHOLD,
    SCORE_LONG_MUTE_SECONDS,
    SCORE_LONG_MUTE_THRESHOLD,
    SCORE_MUTE_THRESHOLD,
)
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, RuleAction
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.score_repo import ScoreRepo
from nonebot_plugin_qguard.services.punishment_service import PunishmentService
from nonebot_plugin_qguard.services.result import ActionResult
from nonebot_plugin_qguard.services.rule_engine import ModerationDecision


@dataclass(frozen=True)
class ScorePenalty:
    action: RuleAction
    threshold: int
    seconds: int = 0


class ScoreResult(BaseModel):
    previous_score: int
    current_score: int
    delta: int
    penalty_action: str | None = None
    penalty_success: bool | None = None


def choose_score_penalty(previous_score: int, current_score: int, default_mute_seconds: int) -> ScorePenalty | None:
    if previous_score < SCORE_KICK_THRESHOLD <= current_score:
        return ScorePenalty(RuleAction.KICK, SCORE_KICK_THRESHOLD)
    if previous_score < SCORE_LONG_MUTE_THRESHOLD <= current_score:
        return ScorePenalty(RuleAction.MUTE, SCORE_LONG_MUTE_THRESHOLD, SCORE_LONG_MUTE_SECONDS)
    if previous_score < SCORE_MUTE_THRESHOLD <= current_score:
        return ScorePenalty(RuleAction.MUTE, SCORE_MUTE_THRESHOLD, default_mute_seconds)
    return None


def action_severity(action: str) -> int:
    if action == RuleAction.KICK_BLACK.value:
        return 4
    if action == RuleAction.KICK.value:
        return 3
    if action == RuleAction.MUTE.value:
        return 2
    if action in {RuleAction.WARN.value, RuleAction.DELETE.value}:
        return 1
    return 0


class ScoreService:
    async def get_score(self, group_id: int, user_id: int) -> ScoreResult:
        async with get_session() as session:
            profile = await ScoreRepo(session).get_or_create_profile(group_id, user_id)
            await session.commit()
            return ScoreResult(previous_score=profile.warning_score, current_score=profile.warning_score, delta=0)

    async def reset_score(self, group_id: int, operator_id: int, user_id: int) -> ActionResult:
        async with get_session() as session:
            profile, previous_score = await ScoreRepo(session).reset_score(group_id, user_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=AuditAction.RESET_SCORE,
                result=AuditResult.SUCCESS,
                metadata={"previous_score": previous_score, "current_score": profile.warning_score},
            )
            await session.commit()
        return ActionResult(success=True, action=str(AuditAction.RESET_SCORE), message=f"已清零积分：{user_id}")

    async def apply_decision_score(
        self,
        ops: GroupOps,
        operator_id: int,
        event,
        decision: ModerationDecision,
    ) -> ScoreResult:
        delta = decision.score_delta if decision.score_delta > 0 else 1
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(event.group_id)
            profile, previous_score, current_score = await ScoreRepo(session).add_score(event.group_id, event.user_id, delta)
            penalty = choose_score_penalty(previous_score, current_score, config.default_mute_seconds)
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=operator_id,
                target_user_id=event.user_id,
                action=AuditAction.ADD_SCORE,
                result=AuditResult.SUCCESS,
                reason=decision.reason,
                related_message_id=event.message_id,
                related_rule_id=decision.rule_id,
                metadata={
                    "delta": delta,
                    "previous_score": previous_score,
                    "current_score": profile.warning_score,
                    "penalty": penalty.action.value if penalty else None,
                    "threshold": penalty.threshold if penalty else None,
                },
            )
            await session.commit()

        result = ScoreResult(previous_score=previous_score, current_score=current_score, delta=delta)
        if penalty is None or action_severity(decision.action) >= action_severity(penalty.action.value):
            return result

        penalty_success = await self._apply_penalty(ops, operator_id, event, decision, penalty)
        result.penalty_action = penalty.action.value
        result.penalty_success = penalty_success
        return result

    async def _apply_penalty(
        self,
        ops: GroupOps,
        operator_id: int,
        event,
        decision: ModerationDecision,
        penalty: ScorePenalty,
    ) -> bool:
        reason = f"违规积分达到 {penalty.threshold} 分：{decision.reason}"
        service = PunishmentService()
        if penalty.action == RuleAction.MUTE:
            result = await service.mute(ops, event.group_id, operator_id, event.user_id, penalty.seconds, reason, event.message_id)
        elif penalty.action == RuleAction.KICK:
            result = await service.kick(ops, event.group_id, operator_id, event.user_id, reason)
        else:
            return False

        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=operator_id,
                target_user_id=event.user_id,
                action=AuditAction.SCORE_PENALTY,
                result=AuditResult.SUCCESS if result.success else AuditResult.FAILED,
                reason=reason,
                related_message_id=event.message_id,
                related_rule_id=decision.rule_id,
                metadata={"penalty": penalty.action.value, "threshold": penalty.threshold, "seconds": penalty.seconds},
                error_message=result.error,
            )
            await session.commit()
        return result.success
