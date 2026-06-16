from typing import Any

from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo


class AuditService:
    async def log(
        self,
        *,
        action: AuditAction | str,
        result: AuditResult | str,
        group_id: int | None = None,
        operator_id: int | None = None,
        target_user_id: int | None = None,
        reason: str | None = None,
        error_message: str | None = None,
        related_message_id: int | None = None,
        related_rule_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        async with get_session() as session:
            await AuditLogRepo(session).create(
                action=action,
                result=result,
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                reason=reason,
                error_message=error_message,
                related_message_id=related_message_id,
                related_rule_id=related_rule_id,
                metadata=metadata,
            )
            await session.commit()
