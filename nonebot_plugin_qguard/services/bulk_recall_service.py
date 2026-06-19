from __future__ import annotations

from dataclasses import dataclass

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService

MAX_BULK_RECALL_COUNT = 500


@dataclass(frozen=True)
class BulkRecallResult:
    attempted: int
    success_count: int
    failed_count: int
    capped: bool = False
    denied_reason: str = ""

    @property
    def success(self) -> bool:
        return not self.denied_reason and self.success_count > 0

    @property
    def message(self) -> str:
        if self.denied_reason:
            return self.denied_reason
        cap_text = f"（最多 {MAX_BULK_RECALL_COUNT} 条，已截断）" if self.capped else ""
        return f"批量撤回完成{cap_text}：尝试 {self.attempted} 条，成功 {self.success_count} 条，失败 {self.failed_count} 条。"


class BulkRecallService:
    async def recall_recent(
        self,
        ops: GroupOps,
        *,
        group_id: int,
        operator_id: int,
        command_message_id: int,
        count: int,
    ) -> BulkRecallResult:
        requested = max(1, count)
        count = min(requested, MAX_BULK_RECALL_COUNT)
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops,
                group_id=group_id,
                operator_id=operator_id,
                required_role=QGuardRole.MINI_ADMIN,
            )
            if not decision.allowed:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.PERMISSION_DENIED,
                    result=AuditResult.SKIPPED,
                    reason=decision.reason,
                    metadata={"selector": "/管 撤回 数量", "count": requested},
                )
                await session.commit()
                return BulkRecallResult(0, 0, 0, denied_reason=decision.reason)

            cached_messages = await MessageCacheRepo(session).latest_in_group(
                group_id,
                limit=max(0, count - 1),
                exclude_message_ids={command_message_id},
            )
            message_ids = [command_message_id, *(item.message_id for item in cached_messages)]

        success_count = 0
        failed_count = 0
        for message_id in message_ids:
            try:
                await ops.delete_msg(message_id)
                success_count += 1
            except Exception:
                failed_count += 1

        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.DELETE_MSG,
                result=AuditResult.SUCCESS if success_count else AuditResult.FAILED,
                related_message_id=command_message_id,
                metadata={
                    "bulk": True,
                    "requested_count": requested,
                    "attempted_count": len(message_ids),
                    "success_count": success_count,
                    "failed_count": failed_count,
                },
            )
            await session.commit()

        return BulkRecallResult(
            attempted=len(message_ids),
            success_count=success_count,
            failed_count=failed_count,
            capped=requested > count,
        )
