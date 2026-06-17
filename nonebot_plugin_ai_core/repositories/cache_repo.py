from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_ai_core.models import AICache


class AICacheRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_valid(self, cache_key: str) -> AICache | None:
        result = await self.session.scalars(
            select(AICache).where(AICache.cache_key == cache_key, AICache.expires_at > datetime.utcnow())
        )
        return result.one_or_none()

    async def upsert(self, item: AICache) -> AICache:
        existing = await self.get_by_key(item.cache_key)
        if existing is None:
            self.session.add(item)
            await self.session.flush()
            return item
        existing.response_text = item.response_text
        existing.expires_at = item.expires_at
        existing.input_hash = item.input_hash
        existing.purpose = item.purpose
        await self.session.flush()
        return existing

    async def get_by_key(self, cache_key: str) -> AICache | None:
        result = await self.session.scalars(select(AICache).where(AICache.cache_key == cache_key))
        return result.one_or_none()
