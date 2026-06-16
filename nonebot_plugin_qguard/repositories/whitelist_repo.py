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

    async def add(self, group_id: int, user_id: int, created_by: int, reason: str | None = None) -> Whitelist:
        item = Whitelist(group_id=group_id, user_id=user_id, created_by=created_by, reason=reason)
        self.session.add(item)
        await self.session.flush()
        return item
