from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.member_cleanup_notice import MemberCleanupNotice


class MemberCleanupNoticeRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int, user_id: int) -> MemberCleanupNotice | None:
        result = await self.session.scalars(
            select(MemberCleanupNotice).where(
                MemberCleanupNotice.group_id == group_id,
                MemberCleanupNotice.user_id == user_id,
            )
        )
        return result.one_or_none()

    async def get_or_create(self, group_id: int, user_id: int) -> MemberCleanupNotice:
        item = await self.get(group_id, user_id)
        if item is None:
            item = MemberCleanupNotice(group_id=group_id, user_id=user_id)
            self.session.add(item)
            await self.session.flush()
        return item

    async def mark_reminded(
        self,
        group_id: int,
        user_id: int,
        *,
        threshold_days: int,
        when: datetime,
    ) -> MemberCleanupNotice:
        item = await self.get_or_create(group_id, user_id)
        item.reminder_count += 1
        item.last_reminded_days = max(item.last_reminded_days, threshold_days)
        item.last_reminded_at = when
        await self.session.flush()
        return item

    async def mark_kicked(self, group_id: int, user_id: int, *, when: datetime) -> MemberCleanupNotice:
        item = await self.get_or_create(group_id, user_id)
        item.pending_cleanup_at = None
        item.pending_cleanup_inactive_days = 0
        item.kicked_at = when
        await self.session.flush()
        return item

    async def mark_pending_cleanup(
        self,
        group_id: int,
        user_id: int,
        *,
        inactive_days: int,
        when: datetime,
    ) -> tuple[MemberCleanupNotice, bool]:
        item = await self.get_or_create(group_id, user_id)
        created = item.pending_cleanup_at is None
        item.pending_cleanup_at = item.pending_cleanup_at or when
        item.pending_cleanup_inactive_days = max(item.pending_cleanup_inactive_days, inactive_days)
        await self.session.flush()
        return item, created

    async def clear_pending_cleanup(self, group_id: int, user_id: int) -> bool:
        item = await self.get(group_id, user_id)
        if item is None or item.pending_cleanup_at is None:
            return False
        item.pending_cleanup_at = None
        item.pending_cleanup_inactive_days = 0
        await self.session.flush()
        return True

    async def list_pending_cleanup(self, group_id: int, limit: int = 200) -> list[MemberCleanupNotice]:
        result = await self.session.scalars(
            select(MemberCleanupNotice)
            .where(
                MemberCleanupNotice.group_id == group_id,
                MemberCleanupNotice.pending_cleanup_at.is_not(None),
                MemberCleanupNotice.kicked_at.is_(None),
            )
            .order_by(MemberCleanupNotice.pending_cleanup_inactive_days.desc(), MemberCleanupNotice.id.asc())
            .limit(limit)
        )
        return list(result)

    async def clear(self, group_id: int, user_id: int) -> int:
        result = await self.session.execute(
            delete(MemberCleanupNotice).where(
                MemberCleanupNotice.group_id == group_id,
                MemberCleanupNotice.user_id == user_id,
            )
        )
        return result.rowcount or 0
