from types import SimpleNamespace
from uuid import uuid4

import pytest

from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.services.newbie_protection_service import NewbieProtectionService


class FakeOps:
    def __init__(self, operator_id: int, target_user_id: int) -> None:
        self.operator_id = operator_id
        self.target_user_id = target_user_id
        self.deleted: list[int] = []
        self.muted: list[tuple[int, int, int]] = []

    async def delete_msg(self, message_id: int) -> None:
        self.deleted.append(message_id)

    async def mute(self, group_id: int, user_id: int, seconds: int) -> None:
        self.muted.append((group_id, user_id, seconds))

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        role = "admin" if user_id == self.operator_id else "member"
        return {"user_id": user_id, "role": role}


class FakeEvent:
    def __init__(self, group_id: int, user_id: int, message_id: int, text: str, segment_types: list[str] | None = None) -> None:
        self.group_id = group_id
        self.user_id = user_id
        self.message_id = message_id
        self._text = text
        self.message = [SimpleNamespace(type=segment_type) for segment_type in (segment_types or [])]

    def get_plaintext(self) -> str:
        return self._text


@pytest.mark.asyncio
async def test_newbie_link_is_deleted_and_muted() -> None:
    group_id = 950000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    operator_id = 999999

    config_service = GroupConfigService()
    await config_service.set_newbie_protection_seconds(group_id, operator_id, 3600)
    await config_service.set_new_member_protection_enabled(group_id, operator_id, True)
    await NewbieProtectionService().record_join(group_id, user_id)

    ops = FakeOps(operator_id, user_id)
    event = FakeEvent(group_id, user_id, 12345, "visit https://example.com")
    handled = await NewbieProtectionService().handle_message(ops, operator_id, event)

    assert handled
    assert ops.deleted == [12345]
    assert ops.muted == [(group_id, user_id, 600)]


@pytest.mark.asyncio
async def test_newbie_normal_message_is_ignored() -> None:
    group_id = 960000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    operator_id = 999999

    await GroupConfigService().set_new_member_protection_enabled(group_id, operator_id, True)
    await NewbieProtectionService().record_join(group_id, user_id)

    ops = FakeOps(operator_id, user_id)
    event = FakeEvent(group_id, user_id, 23456, "hello")
    handled = await NewbieProtectionService().handle_message(ops, operator_id, event)

    assert not handled
    assert ops.deleted == []
    assert ops.muted == []


@pytest.mark.asyncio
async def test_newbie_link_block_can_be_disabled() -> None:
    group_id = 961000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    operator_id = 999999

    config_service = GroupConfigService()
    await config_service.set_new_member_protection_enabled(group_id, operator_id, True)
    await config_service.set_newbie_block_links(group_id, operator_id, False)
    await NewbieProtectionService().record_join(group_id, user_id)

    ops = FakeOps(operator_id, user_id)
    event = FakeEvent(group_id, user_id, 34567, "visit https://example.com")
    handled = await NewbieProtectionService().handle_message(ops, operator_id, event)

    assert not handled
    assert ops.deleted == []
    assert ops.muted == []
