from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.blacklist import Blacklist


class BlacklistRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_blacklisted(self, group_id: int, user_id: int) -> bool:
        result = await self.session.scalars(
            select(Blacklist).where(
                Blacklist.user_id == user_id,
                or_(Blacklist.group_id == group_id, Blacklist.group_id.is_(None)),
                or_(Blacklist.expires_at.is_(None), Blacklist.expires_at > datetime.utcnow()),
            )
        )
        return result.first() is not None

    async def get(self, group_id: int | None, user_id: int) -> Blacklist | None:
        result = await self.session.scalars(
            select(Blacklist).where(Blacklist.group_id == group_id, Blacklist.user_id == user_id)
        )
        return result.one_or_none()

    async def add(self, group_id: int | None, user_id: int, created_by: int, reason: str | None = None) -> Blacklist:
        item = await self.get(group_id, user_id)
        if item is None:
            item = Blacklist(group_id=group_id, user_id=user_id, created_by=created_by, reason=reason)
            self.session.add(item)
        else:
            item.created_by = created_by
            item.reason = reason
            item.expires_at = None
        await self.session.flush()
        return item

    async def remove(self, group_id: int | None, user_id: int) -> bool:
        item = await self.get(group_id, user_id)
        if item is None:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def list_group(self, group_id: int, limit: int = 50) -> list[Blacklist]:
        result = await self.session.scalars(
            select(Blacklist)
            .where(
                Blacklist.group_id == group_id,
                or_(Blacklist.expires_at.is_(None), Blacklist.expires_at > datetime.utcnow()),
            )
            .order_by(Blacklist.id.desc())
            .limit(limit)
        )
        return list(result)
