from uuid import uuid4

import pytest

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.group_setting_service import GroupSettingService
from nonebot_plugin_qguard.services.patrol_service import PatrolService


class FakeOps:
    def __init__(self, group_name: str = "old", bot_role: str = "owner") -> None:
        self.group_name = group_name
        self.bot_role = bot_role
        self.names: list[tuple[int, str]] = []
        self.anonymous: list[tuple[int, bool]] = []
        self.whole_mutes: list[tuple[int, bool]] = []
        self.titles: list[tuple[int, int, str, int]] = []

    async def set_group_name(self, group_id: int, name: str) -> None:
        self.names.append((group_id, name))
        self.group_name = name

    async def get_group_info(self, group_id: int, no_cache: bool = True):
        return {"group_id": group_id, "group_name": self.group_name}

    async def set_group_anonymous(self, group_id: int, enable: bool) -> None:
        self.anonymous.append((group_id, enable))

    async def whole_mute(self, group_id: int, enable: bool) -> None:
        self.whole_mutes.append((group_id, enable))

    async def set_special_title(self, group_id: int, user_id: int, title: str, duration: int = -1) -> None:
        self.titles.append((group_id, user_id, title, duration))

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        return {"group_id": group_id, "user_id": user_id, "role": self.bot_role}


@pytest.mark.asyncio
async def test_group_name_lock_and_repair() -> None:
    group_id = 990000000 + (uuid4().int % 100000000)
    ops = FakeOps(group_name="old")

    result = await GroupSettingService().lock_group_name(ops, group_id, 1, "locked")
    assert result.success
    assert ops.names == [(group_id, "locked")]

    ops.group_name = "changed"
    repair = await GroupSettingService().repair_group_name(ops, group_id, 1)
    assert repair.fixed == 1
    assert ops.names[-1] == (group_id, "locked")

    async with get_session() as session:
        config = await GroupConfigRepo(session).get_or_create(group_id)
        assert config.group_name_lock_enabled
        assert config.locked_group_name == "locked"


@pytest.mark.asyncio
async def test_anonymous_lock_and_patrol_settings() -> None:
    group_id = 991000000 + (uuid4().int % 100000000)
    ops = FakeOps()

    result = await GroupSettingService().lock_anonymous(ops, group_id, 1, False)
    assert result.success
    assert ops.anonymous == [(group_id, False)]

    patrol = await PatrolService().patrol_group_settings(ops, group_id, 1)
    assert patrol.checked >= 1
    assert ops.anonymous[-1] == (group_id, False)


@pytest.mark.asyncio
async def test_set_whole_mute_records_action() -> None:
    group_id = 991500000 + (uuid4().int % 100000000)
    ops = FakeOps()

    result = await GroupSettingService().set_whole_mute(ops, group_id, 1, True)

    assert result.success
    assert ops.whole_mutes == [(group_id, True)]


@pytest.mark.asyncio
async def test_special_title_requires_bot_owner() -> None:
    group_id = 992000000 + (uuid4().int % 100000000)
    ops = FakeOps(bot_role="admin")

    result = await GroupSettingService().set_special_title(ops, group_id, 1, 2, "title", bot_user_id=9)

    assert not result.success
    assert "只有群主" in result.message
    assert ops.titles == []


@pytest.mark.asyncio
async def test_special_title_sets_when_bot_owner() -> None:
    group_id = 993000000 + (uuid4().int % 100000000)
    ops = FakeOps(bot_role="owner")

    result = await GroupSettingService().set_special_title(ops, group_id, 1, 2, "title", bot_user_id=9)

    assert result.success
    assert ops.titles == [(group_id, 2, "title", -1)]
