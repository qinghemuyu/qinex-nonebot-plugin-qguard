from uuid import uuid4

import pytest

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.config import Config
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.services.member_role_service import MemberRoleService
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.punishment_service import PunishmentService


class FakeOps:
    def __init__(self) -> None:
        self.muted: list[tuple[int, int, int]] = []
        self.kicked: list[tuple[int, int, bool]] = []

    async def mute(self, group_id: int, user_id: int, seconds: int) -> None:
        self.muted.append((group_id, user_id, seconds))

    async def kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        self.kicked.append((group_id, user_id, reject_add_request))

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        return {"user_id": user_id, "role": "member"}


def test_permission_role_order() -> None:
    assert QGuardRole.SUPER_ADMIN > QGuardRole.GROUP_OWNER
    assert QGuardRole.GROUP_OWNER > QGuardRole.GROUP_ADMIN
    assert QGuardRole.GROUP_ADMIN > QGuardRole.MINI_ADMIN
    assert QGuardRole.MINI_ADMIN > QGuardRole.TRUSTED
    assert QGuardRole.TRUSTED > QGuardRole.MEMBER


def test_default_super_admin_owner() -> None:
    assert Config().qguard_super_admins == {1348984838}


@pytest.mark.asyncio
async def test_mini_admin_can_mute_but_cannot_kick() -> None:
    group_id = 880000000 + (uuid4().int % 100000000)
    operator_id = 10000 + (uuid4().int % 100000)
    target_id = 20000 + (uuid4().int % 100000)
    await MemberRoleService().set_role(group_id, 1, operator_id, QGuardRole.MINI_ADMIN)

    ops = FakeOps()
    mute = await PunishmentService().mute(ops, group_id, operator_id, target_id, 60, "test")
    kick = await PunishmentService().kick(ops, group_id, operator_id, target_id, "test")

    assert mute.success
    assert not kick.success
    assert ops.muted == [(group_id, target_id, 60)]
    assert ops.kicked == []


@pytest.mark.asyncio
async def test_trusted_role_is_protected_from_auto_action() -> None:
    group_id = 881000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    await MemberRoleService().set_role(group_id, 1, user_id, QGuardRole.TRUSTED)

    async with get_session() as session:
        protected = await PermissionService(session).is_protected_from_auto_action(FakeOps(), group_id, user_id)

    assert protected
