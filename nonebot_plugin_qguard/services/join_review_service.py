from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from typing import ClassVar

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.ad_keyword_repo import AdKeywordRepo
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.blacklist_repo import BlacklistRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.ad_keyword_defaults import (
    DEFAULT_AD_KEYWORD_OPERATOR_ID,
    DEFAULT_AD_KEYWORDS,
)
from nonebot_plugin_qguard.services.anti_ad_service import AntiAdService
from nonebot_plugin_qguard.services.result import ActionResult


@dataclass(frozen=True)
class JoinReviewResult:
    handled: bool
    approved: bool | None = None
    reason: str = ""


class JoinReviewService:
    _request_history: ClassVar[dict[tuple[int, int], deque[float]]] = defaultdict(deque)
    _repeat_window_seconds = 60.0
    _repeat_threshold = 3

    @classmethod
    def reset_request_history(cls) -> None:
        cls._request_history.clear()

    async def set_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_join_review_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_JOIN_REVIEW,
                result=AuditResult.SUCCESS,
                metadata={"join_review_enabled": enabled},
            )
            await session.commit()
        return ActionResult(
            success=True,
            action=str(AuditAction.SET_JOIN_REVIEW),
            message=f"入群审核已{'开启' if config.join_review_enabled else '关闭'}。",
        )

    async def set_answer(self, group_id: int, operator_id: int, answer: str) -> ActionResult:
        answer = answer.strip()
        if not answer:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_JOIN_REVIEW_ANSWER),
                message="入群暗号不能为空。",
            )

        async with get_session() as session:
            await GroupConfigRepo(session).set_join_review_answer(group_id, answer)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_JOIN_REVIEW_ANSWER,
                result=AuditResult.SUCCESS,
                metadata={"answer_length": len(answer)},
            )
            await session.commit()
        return ActionResult(success=True, action=str(AuditAction.SET_JOIN_REVIEW_ANSWER), message="入群暗号已设置。")

    async def set_reject_reason(self, group_id: int, operator_id: int, reason: str) -> ActionResult:
        reason = reason.strip()
        if not reason:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_JOIN_REVIEW_REJECT_REASON),
                message="入群拒绝理由不能为空。",
            )

        async with get_session() as session:
            await GroupConfigRepo(session).set_join_review_reject_reason(group_id, reason)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_JOIN_REVIEW_REJECT_REASON,
                result=AuditResult.SUCCESS,
            )
            await session.commit()
        return ActionResult(
            success=True,
            action=str(AuditAction.SET_JOIN_REVIEW_REJECT_REASON),
            message="入群拒绝理由已设置。",
        )

    async def review_group_request(
        self,
        ops: GroupOps,
        *,
        group_id: int,
        user_id: int,
        flag: str,
        sub_type: str,
        comment: str | None,
        operator_id: int,
    ) -> JoinReviewResult:
        if sub_type != "add":
            return JoinReviewResult(handled=False, reason="非主动入群申请。")

        comment_text = comment or ""
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            if not config.enabled:
                await session.commit()
                return JoinReviewResult(handled=False, reason="QGuard 未开启。")

            is_blacklisted = await BlacklistRepo(session).is_blacklisted(group_id, user_id)
            if is_blacklisted:
                return await self._handle_request(
                    session,
                    ops,
                    group_id=group_id,
                    user_id=user_id,
                    flag=flag,
                    sub_type=sub_type,
                    operator_id=operator_id,
                    approve=False,
                    reason="黑名单用户禁止入群。",
                    metadata={"reason_type": "blacklist", "comment": comment_text},
                )

            if not config.join_review_enabled:
                await session.commit()
                return JoinReviewResult(handled=False, reason="入群审核未开启。")

            if self._is_repeated_request(group_id, user_id):
                return await self._handle_request(
                    session,
                    ops,
                    group_id=group_id,
                    user_id=user_id,
                    flag=flag,
                    sub_type=sub_type,
                    operator_id=operator_id,
                    approve=False,
                    reason="入群申请过于频繁。",
                    metadata={"reason_type": "repeat", "comment": comment_text},
                )

            if not comment_text.strip():
                return await self._handle_request(
                    session,
                    ops,
                    group_id=group_id,
                    user_id=user_id,
                    flag=flag,
                    sub_type=sub_type,
                    operator_id=operator_id,
                    approve=False,
                    reason="入群申请理由为空。",
                    metadata={"reason_type": "empty", "comment": comment_text},
                )

            keyword_repo = AdKeywordRepo(session)
            added_keywords = await keyword_repo.add_missing(
                group_id,
                DEFAULT_AD_KEYWORDS,
                DEFAULT_AD_KEYWORD_OPERATOR_ID,
            )
            if added_keywords:
                await session.commit()
            ad_keywords = [item.keyword for item in await keyword_repo.list_enabled(group_id)]
            ad_decision = AntiAdService().check(
                comment_text,
                link_count=comment_text.count("http://") + comment_text.count("https://"),
                extra_keywords=ad_keywords,
            )
            if ad_decision is not None:
                return await self._handle_request(
                    session,
                    ops,
                    group_id=group_id,
                    user_id=user_id,
                    flag=flag,
                    sub_type=sub_type,
                    operator_id=operator_id,
                    approve=False,
                    reason="入群申请包含广告或引流内容。",
                    metadata={"reason_type": "ad", "comment": comment_text, "decision": ad_decision},
                )

            answer = config.join_review_answer.strip()
            if not answer:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=user_id,
                    action=AuditAction.JOIN_REJECT,
                    result=AuditResult.SKIPPED,
                    reason="入群审核已开启但未设置暗号。",
                    metadata={"comment": comment_text},
                )
                await session.commit()
                return JoinReviewResult(handled=False, reason="入群审核已开启但未设置暗号。")

            approve = answer in comment_text
            reason = "" if approve else (config.join_review_reject_reason or "入群验证未通过。")
            return await self._handle_request(
                session,
                ops,
                group_id=group_id,
                user_id=user_id,
                flag=flag,
                sub_type=sub_type,
                operator_id=operator_id,
                approve=approve,
                reason=reason,
                metadata={"reason_type": "answer", "comment": comment_text, "answer_length": len(answer)},
            )

    def _is_repeated_request(self, group_id: int, user_id: int) -> bool:
        current = monotonic()
        history = self._request_history[(group_id, user_id)]
        while history and current - history[0] > self._repeat_window_seconds:
            history.popleft()
        history.append(current)
        return len(history) >= self._repeat_threshold

    async def _handle_request(
        self,
        session,
        ops: GroupOps,
        *,
        group_id: int,
        user_id: int,
        flag: str,
        sub_type: str,
        operator_id: int,
        approve: bool,
        reason: str,
        metadata: dict[str, object],
    ) -> JoinReviewResult:
        action = AuditAction.JOIN_APPROVE if approve else AuditAction.JOIN_REJECT
        try:
            await ops.handle_group_add_request(flag, sub_type, approve, reason)
        except Exception as exc:
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=action,
                result=AuditResult.FAILED,
                reason=reason,
                error_message=str(exc),
                metadata=metadata,
            )
            await session.commit()
            return JoinReviewResult(handled=True, approved=None, reason=f"处理入群申请失败：{exc}")

        await AuditLogRepo(session).create(
            group_id=group_id,
            operator_id=operator_id,
            target_user_id=user_id,
            action=action,
            result=AuditResult.SUCCESS,
            reason=reason,
            metadata=metadata,
        )
        await session.commit()
        return JoinReviewResult(handled=True, approved=approve, reason=reason)
