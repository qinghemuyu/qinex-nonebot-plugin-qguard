from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.card_lock import CardLock


class CardLockRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int, user_id: int) -> CardLock | None:
        result = await self.session.scalars(
            select(CardLock).where(CardLock.group_id == group_id, CardLock.user_id == user_id)
        )
        return result.one_or_none()

    async def upsert(self, group_id: int, user_id: int, locked_card: str, created_by: int) -> CardLock:
        item = await self.get(group_id, user_id)
        if item is None:
            item = CardLock(group_id=group_id, user_id=user_id, locked_card=locked_card, created_by=created_by)
            self.session.add(item)
        else:
            item.locked_card = locked_card
            item.enabled = True
            item.created_by = created_by
            item.last_error = None
            item.failure_count = 0
        await self.session.flush()
        return item

    async def disable(self, group_id: int, user_id: int) -> CardLock | None:
        item = await self.get(group_id, user_id)
        if item is not None:
            item.enabled = False
            await self.session.flush()
        return item

    async def list_enabled(self, group_id: int, limit: int = 100) -> list[CardLock]:
        result = await self.session.scalars(
            select(CardLock)
            .where(CardLock.group_id == group_id, CardLock.enabled.is_(True))
            .order_by(CardLock.id.asc())
            .limit(limit)
        )
        return list(result)

    async def list_all_enabled(self, limit: int = 1000) -> list[CardLock]:
        result = await self.session.scalars(
            select(CardLock).where(CardLock.enabled.is_(True)).order_by(CardLock.id.asc()).limit(limit)
        )
        return list(result)

    async def mark_seen(self, item: CardLock, current_card: str) -> None:
        item.last_seen_card = current_card
        await self.session.flush()

    async def mark_fixed(self, item: CardLock, current_card: str) -> None:
        item.violation_count += 1
        item.failure_count = 0
        item.last_seen_card = current_card
        item.last_fixed_at = datetime.utcnow()
        item.last_fixed_by_plugin_at = datetime.utcnow()
        item.last_error = None
        await self.session.flush()

    async def mark_failed(self, item: CardLock, current_card: str, error: str) -> None:
        item.failure_count += 1
        item.last_seen_card = current_card
        item.last_error = error
        await self.session.flush()
