from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.whitelist import Whitelist


class WhitelistRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_whitelisted(self, group_id: int, user_id: int) -> bool:
        result = await self.session.scalars(
            select(Whitelist).where(Whitelist.group_id == group_id, Whitelist.user_id == user_id)
        )
        return result.first() is not None

    async def get(self, group_id: int, user_id: int) -> Whitelist | None:
        result = await self.session.scalars(
            select(Whitelist).where(Whitelist.group_id == group_id, Whitelist.user_id == user_id)
        )
        return result.one_or_none()

    async def add(self, group_id: int, user_id: int, created_by: int, reason: str | None = None) -> Whitelist:
        item = await self.get(group_id, user_id)
        if item is None:
            item = Whitelist(group_id=group_id, user_id=user_id, created_by=created_by, reason=reason)
            self.session.add(item)
        else:
            item.created_by = created_by
            item.reason = reason
        await self.session.flush()
        return item

    async def remove(self, group_id: int, user_id: int) -> bool:
        item = await self.get(group_id, user_id)
        if item is None:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def list_group(self, group_id: int, limit: int = 50) -> list[Whitelist]:
        result = await self.session.scalars(
            select(Whitelist).where(Whitelist.group_id == group_id).order_by(Whitelist.id.desc()).limit(limit)
        )
        return list(result)
