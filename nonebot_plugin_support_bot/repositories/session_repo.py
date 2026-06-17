from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import SupportSession


class SupportSessionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self, group_id: int, user_id: int, now: datetime | None = None) -> SupportSession | None:
        now = now or datetime.utcnow()
        result = await self.session.scalars(
            select(SupportSession).where(
                SupportSession.group_id == group_id,
                SupportSession.user_id == user_id,
                SupportSession.expires_at > now,
            )
        )
        return result.first()

    async def upsert(
        self,
        *,
        group_id: int,
        user_id: int,
        state: str,
        intent: str,
        context_json: str,
        ttl_seconds: int,
    ) -> SupportSession:
        now = datetime.utcnow()
        item = await self.get_active(group_id, user_id, now)
        if item is None:
            item = SupportSession(
                session_id=f"{group_id}:{user_id}:{int(now.timestamp())}",
                group_id=group_id,
                user_id=user_id,
            )
            self.session.add(item)
        item.state = state
        item.intent = intent
        item.context_json = context_json
        item.last_active_at = now
        item.expires_at = now + timedelta(seconds=ttl_seconds)
        await self.session.flush()
        return item
