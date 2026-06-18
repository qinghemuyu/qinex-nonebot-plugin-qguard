from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import SupportHarassmentMemory


class SupportHarassmentRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, group_id: int, user_id: int) -> SupportHarassmentMemory:
        result = await self.session.scalars(
            select(SupportHarassmentMemory).where(
                SupportHarassmentMemory.group_id == group_id,
                SupportHarassmentMemory.user_id == user_id,
            )
        )
        item = result.one_or_none()
        if item is not None:
            return item
        item = SupportHarassmentMemory(group_id=group_id, user_id=user_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def record(
        self,
        *,
        group_id: int,
        user_id: int,
        severity: int,
        reason: str,
        text: str,
        window_seconds: int,
        score_threshold: int,
        score_cooldown_seconds: int,
        base_score_delta: int,
        max_score_delta: int,
        now: datetime | None = None,
    ) -> tuple[SupportHarassmentMemory, int, bool]:
        now = now or datetime.utcnow()
        item = await self.get_or_create(group_id, user_id)
        previous_anger = item.anger_score

        if item.last_event_at is not None:
            seconds_since_last = (now - item.last_event_at).total_seconds()
            if seconds_since_last > window_seconds:
                item.anger_score = max(0, item.anger_score - 2)

        item.anger_score += max(1, severity)
        item.total_strikes += 1
        item.last_reason = reason[:128]
        item.last_text = text[:1000]
        item.last_event_at = now

        can_score = item.anger_score >= score_threshold and previous_anger < item.anger_score
        if can_score and item.last_score_at is not None:
            can_score = (now - item.last_score_at).total_seconds() >= score_cooldown_seconds

        score_delta = 0
        if can_score:
            extra = max(0, item.anger_score - score_threshold) // 2
            score_delta = min(max_score_delta, max(1, base_score_delta + extra))
            item.score_punish_count += 1
            item.last_score_at = now
            item.anger_score = max(0, item.anger_score - score_threshold + 1)

        await self.session.flush()
        return item, score_delta, item.anger_score >= score_threshold
