from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import SupportNoAnswer


class SupportNoAnswerRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        group_id: int,
        user_id: int,
        question: str,
        reason: str,
    ) -> SupportNoAnswer:
        item = SupportNoAnswer(
            group_id=group_id,
            user_id=user_id,
            question=question.strip()[:4000],
            reason=reason,
        )
        self.session.add(item)
        await self.session.flush()
        item.record_no = f"N{item.id:06d}"
        await self.session.flush()
        return item

    async def mark_notified(self, record_no: str) -> None:
        item = await self.get_by_record_no(record_no)
        if item is None:
            return
        item.notified_owner = True
        item.updated_at = datetime.utcnow()
        await self.session.flush()

    async def get_by_record_no(self, record_no: str) -> SupportNoAnswer | None:
        result = await self.session.scalars(
            select(SupportNoAnswer).where(SupportNoAnswer.record_no == record_no.upper())
        )
        return result.one_or_none()
