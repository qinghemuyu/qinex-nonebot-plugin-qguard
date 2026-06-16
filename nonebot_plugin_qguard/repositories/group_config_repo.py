from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.group_config import GroupConfig


class GroupConfigRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int) -> GroupConfig | None:
        return await self.session.get(GroupConfig, group_id)

    async def get_or_create(self, group_id: int) -> GroupConfig:
        config = await self.get(group_id)
        if config is None:
            config = GroupConfig(group_id=group_id)
            self.session.add(config)
            await self.session.flush()
        return config

    async def set_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.enabled = enabled
        await self.session.flush()
        return config

    async def set_card_lock_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.card_lock_enabled = enabled
        await self.session.flush()
        return config

    async def list_card_lock_enabled_groups(self) -> list[GroupConfig]:
        result = await self.session.scalars(
            select(GroupConfig).where(GroupConfig.enabled.is_(True), GroupConfig.card_lock_enabled.is_(True))
        )
        return list(result)
