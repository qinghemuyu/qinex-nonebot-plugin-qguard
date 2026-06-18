from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.group_plugin_config import GroupPluginConfig


class GroupPluginConfigRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int, plugin_id: str) -> GroupPluginConfig | None:
        result = await self.session.scalars(
            select(GroupPluginConfig).where(
                GroupPluginConfig.group_id == group_id,
                GroupPluginConfig.plugin_id == plugin_id,
            )
        )
        return result.one_or_none()

    async def get_or_create(self, group_id: int, plugin_id: str) -> GroupPluginConfig:
        item = await self.get(group_id, plugin_id)
        if item is not None:
            return item
        item = GroupPluginConfig(group_id=group_id, plugin_id=plugin_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_by_group(self, group_id: int) -> list[GroupPluginConfig]:
        result = await self.session.scalars(
            select(GroupPluginConfig).where(GroupPluginConfig.group_id == group_id)
        )
        return list(result)

    async def set_enabled(
        self,
        group_id: int,
        plugin_id: str,
        enabled: bool | None,
        updated_by: int | None,
    ) -> GroupPluginConfig:
        item = await self.get_or_create(group_id, plugin_id)
        item.enabled = enabled
        item.updated_by = updated_by
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    async def set_permission_overrides(
        self,
        group_id: int,
        plugin_id: str,
        overrides: dict[str, int],
        updated_by: int | None,
    ) -> GroupPluginConfig:
        item = await self.get_or_create(group_id, plugin_id)
        item.permission_override_json = json.dumps(overrides, ensure_ascii=False) if overrides else None
        item.updated_by = updated_by
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    @staticmethod
    def permission_overrides(item: GroupPluginConfig | None) -> dict[str, int]:
        return _load_json_dict(None if item is None else item.permission_override_json)


def _load_json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
