from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_ai_core.models import AIRateLimit


class AIRateLimitRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_count(self, scope_type: str, scope_id: int, window_date: date) -> int:
        row = await self.get(scope_type, scope_id, window_date)
        return 0 if row is None else row.used_count

    async def increment(self, scope_type: str, scope_id: int, window_date: date, *, tokens: int = 0) -> AIRateLimit:
        row = await self.get(scope_type, scope_id, window_date)
        if row is None:
            row = AIRateLimit(
                scope_type=scope_type,
                scope_id=scope_id,
                window_date=window_date,
                used_count=1,
                used_tokens=tokens,
            )
            self.session.add(row)
        else:
            row.used_count += 1
            row.used_tokens += tokens
            row.updated_at = datetime.utcnow()
        await self.session.flush()
        return row

    async def get(self, scope_type: str, scope_id: int, window_date: date) -> AIRateLimit | None:
        result = await self.session.scalars(
            select(AIRateLimit).where(
                AIRateLimit.scope_type == scope_type,
                AIRateLimit.scope_id == scope_id,
                AIRateLimit.window_date == window_date,
            )
        )
        return result.one_or_none()
