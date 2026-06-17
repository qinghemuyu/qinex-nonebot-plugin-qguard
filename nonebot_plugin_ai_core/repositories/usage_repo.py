from datetime import date, datetime, time

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_ai_core.models import AIUsageLog


class AIUsageLogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, item: AIUsageLog) -> AIUsageLog:
        self.session.add(item)
        await self.session.flush()
        return item

    async def today_summary(self, today: date) -> dict[str, int]:
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        result = await self.session.execute(
            select(
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
                func.coalesce(func.sum(case((AIUsageLog.success.is_(True), 1), else_=0)), 0),
            ).where(AIUsageLog.created_at >= start, AIUsageLog.created_at <= end)
        )
        total_calls, total_tokens, success_calls = result.one()
        return {
            "total_calls": int(total_calls or 0),
            "success_calls": int(success_calls or 0),
            "failed_calls": int((total_calls or 0) - (success_calls or 0)),
            "total_tokens": int(total_tokens or 0),
        }
