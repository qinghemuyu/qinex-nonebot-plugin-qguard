from datetime import datetime
from uuid import uuid4

import pytest

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService


@pytest.mark.asyncio
async def test_auto_patrol_due_groups() -> None:
    group_id = 994000000 + (uuid4().int % 100000000)
    service = GroupConfigService()

    await service.set_auto_patrol_interval_seconds(group_id, 1, 120)
    await service.set_auto_patrol_enabled(group_id, 1, True)

    async with get_session() as session:
        repo = GroupConfigRepo(session)
        due = await repo.list_auto_patrol_due_groups(datetime.utcnow())
        assert any(config.group_id == group_id for config in due)

        await repo.mark_auto_patrol_ran(group_id, datetime.utcnow())
        await session.commit()

    async with get_session() as session:
        due = await GroupConfigRepo(session).list_auto_patrol_due_groups(datetime.utcnow())
        assert all(config.group_id != group_id for config in due)


@pytest.mark.asyncio
async def test_auto_patrol_interval_minimum() -> None:
    group_id = 995000000 + (uuid4().int % 100000000)

    result = await GroupConfigService().set_auto_patrol_interval_seconds(group_id, 1, 5)
    assert result.success

    async with get_session() as session:
        config = await GroupConfigRepo(session).get_or_create(group_id)
        assert config.auto_patrol_interval_seconds == 60
