from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.config import Config
from nonebot_plugin_support_bot.models import SupportGroupConfig


class SupportGroupConfigRepo:
    def __init__(self, session: AsyncSession, config: Config | None = None) -> None:
        self.session = session
        self.config = config or Config()

    async def get(self, group_id: int) -> SupportGroupConfig | None:
        result = await self.session.scalars(
            select(SupportGroupConfig).where(SupportGroupConfig.group_id == group_id)
        )
        return result.one_or_none()

    async def get_or_create(self, group_id: int) -> SupportGroupConfig:
        item = await self.get(group_id)
        if item is not None:
            return item
        item = SupportGroupConfig(
            group_id=group_id,
            enabled=self.config.support_bot_enabled,
            trigger_mode=self.config.support_bot_trigger_mode,
            smart_listen=self.config.support_bot_enable_smart_listen,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def set_enabled(self, group_id: int, enabled: bool, updated_by: int | None) -> SupportGroupConfig:
        item = await self.get_or_create(group_id)
        item.enabled = enabled
        item.updated_by = updated_by
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    async def set_mode(self, group_id: int, mode: str, updated_by: int | None) -> SupportGroupConfig:
        item = await self.get_or_create(group_id)
        item.trigger_mode = mode
        item.smart_listen = mode == "smart"
        item.updated_by = updated_by
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item
