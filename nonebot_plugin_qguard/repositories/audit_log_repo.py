import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.audit_log import AuditLog


class AuditLogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
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
    ) -> AuditLog:
        item = AuditLog(
            group_id=group_id,
            operator_id=operator_id,
            target_user_id=target_user_id,
            action=str(action),
            reason=reason,
            result=str(result),
            error_message=error_message,
            related_message_id=related_message_id,
            related_rule_id=related_rule_id,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def latest(self, group_id: int | None = None, limit: int = 10) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
        if group_id is not None:
            stmt = stmt.where(AuditLog.group_id == group_id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def by_user(self, group_id: int, user_id: int, limit: int = 10) -> list[AuditLog]:
        result = await self.session.scalars(
            select(AuditLog)
            .where(AuditLog.group_id == group_id, AuditLog.target_user_id == user_id)
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
        return list(result)
