from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qfun.config import Config
from nonebot_plugin_qfun.models import QFunGroupConfig


class QFunGroupConfigRepo:
    def __init__(self, session: AsyncSession, config: Config | None = None) -> None:
        self.session = session
        self.config = config or Config()

    async def get_or_create(self, group_id: int) -> QFunGroupConfig:
        result = await self.session.scalars(select(QFunGroupConfig).where(QFunGroupConfig.group_id == group_id))
        item = result.one_or_none()
        if item is None:
            item = QFunGroupConfig(
                group_id=group_id,
                enabled=self.config.qfun_default_enabled,
                wordcloud_schedule_time=self.config.qfun_wordcloud_default_time,
                wordcloud_schedule_period=self.config.qfun_wordcloud_default_period,
            )
            self.session.add(item)
            await self.session.flush()
        return item

    async def set_enabled(self, group_id: int, enabled: bool, operator_id: int | None) -> QFunGroupConfig:
        item = await self.get_or_create(group_id)
        item.enabled = enabled
        item.updated_by = operator_id
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    async def set_wordcloud_schedule(
        self,
        group_id: int,
        *,
        enabled: bool,
        schedule_time: str | None = None,
        period: str | None = None,
        operator_id: int | None = None,
    ) -> QFunGroupConfig:
        item = await self.get_or_create(group_id)
        item.wordcloud_schedule_enabled = enabled
        if schedule_time is not None:
            item.wordcloud_schedule_time = schedule_time
        if period is not None:
            item.wordcloud_schedule_period = period
        item.updated_by = operator_id
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    async def list_due_wordcloud_groups(self, now: datetime) -> list[QFunGroupConfig]:
        today = now.date().isoformat()
        current_time = now.strftime("%H:%M")
        result = await self.session.scalars(
            select(QFunGroupConfig).where(
                QFunGroupConfig.enabled.is_(True),
                QFunGroupConfig.wordcloud_schedule_enabled.is_(True),
                QFunGroupConfig.wordcloud_schedule_time == current_time,
                QFunGroupConfig.last_wordcloud_sent_on != today,
            )
        )
        return list(result)

    async def mark_wordcloud_sent(self, group_id: int, sent_on: str) -> None:
        item = await self.get_or_create(group_id)
        item.last_wordcloud_sent_on = sent_on
        item.updated_at = datetime.utcnow()
        await self.session.flush()
