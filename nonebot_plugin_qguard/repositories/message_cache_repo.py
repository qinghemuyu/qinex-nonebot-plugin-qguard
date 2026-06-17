from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.message_cache import MessageCache


class MessageCacheRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, item: MessageCache) -> MessageCache:
        existing = await self.session.get(MessageCache, item.message_id)
        if existing is None:
            self.session.add(item)
            await self.session.flush()
            return item
        existing.group_id = item.group_id
        existing.user_id = item.user_id
        existing.plain_text = item.plain_text
        existing.raw_message_json = item.raw_message_json
        existing.image_count = item.image_count
        existing.at_count = item.at_count
        existing.link_count = item.link_count
        existing.expires_at = item.expires_at
        await self.session.flush()
        return existing

    async def cleanup_expired(self) -> int:
        result = await self.session.execute(delete(MessageCache).where(MessageCache.expires_at < datetime.utcnow()))
        return result.rowcount or 0

    async def get_in_group(self, group_id: int, message_id: int) -> MessageCache | None:
        result = await self.session.scalars(
            select(MessageCache).where(MessageCache.group_id == group_id, MessageCache.message_id == message_id)
        )
        return result.one_or_none()

    async def latest_by_user(self, group_id: int, user_id: int, limit: int = 10) -> list[MessageCache]:
        result = await self.session.scalars(
            select(MessageCache)
            .where(MessageCache.group_id == group_id, MessageCache.user_id == user_id)
            .order_by(MessageCache.created_at.desc())
            .limit(limit)
        )
        return list(result)
