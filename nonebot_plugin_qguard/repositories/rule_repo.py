from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.enums import RuleAction, RuleType
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

    async def list_all(self, group_id: int, limit: int = 50) -> list[Rule]:
        result = await self.session.scalars(
            select(Rule).where(Rule.group_id == group_id).order_by(Rule.id.desc()).limit(limit)
        )
        return list(result)

    async def get(self, rule_id: int) -> Rule | None:
        return await self.session.get(Rule, rule_id)

    async def create(
        self,
        *,
        group_id: int,
        rule_type: RuleType,
        pattern: str,
        action: RuleAction,
        created_by: int,
        mute_seconds: int = 0,
        delete_message: bool = False,
        score_delta: int = 1,
        priority: int = 100,
    ) -> Rule:
        item = Rule(
            group_id=group_id,
            rule_type=str(rule_type),
            pattern=pattern,
            action=str(action),
            created_by=created_by,
            mute_seconds=mute_seconds,
            delete_message=delete_message,
            score_delta=score_delta,
            priority=priority,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def disable(self, rule_id: int, group_id: int) -> Rule | None:
        item = await self.get(rule_id)
        if item is None or item.group_id != group_id:
            return None
        item.enabled = False
        await self.session.flush()
        return item
