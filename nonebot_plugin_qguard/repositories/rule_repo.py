from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.rule import Rule


class RuleRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_enabled(self, group_id: int, limit: int = 100) -> list[Rule]:
        result = await self.session.scalars(
            select(Rule)
            .where(Rule.group_id == group_id, Rule.enabled.is_(True))
            .order_by(Rule.priority.asc(), Rule.id.asc())
            .limit(limit)
        )
        return list(result)
