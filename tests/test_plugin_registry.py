from uuid import uuid4

from nonebot_plugin_ai_core.qguard_registry import get_qguard_descriptor as get_ai_descriptor
from nonebot_plugin_group_wiki.qguard_registry import get_qguard_descriptor as get_wiki_descriptor
from nonebot_plugin_qfun.qguard_registry import get_qguard_descriptor as get_qfun_descriptor
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.qguard_registry import get_qguard_descriptor
from nonebot_plugin_qguard.registry import (
    RegistryContext,
    build_help_text_for_context,
    build_help_text,
    build_plugin_help_text,
    clear_registry,
    register_plugin,
)
from nonebot_plugin_qguard.services.registered_permission_service import RegisteredCommandPermissionService
from nonebot_plugin_qguard.services.plugin_center_service import PluginCenterService
from nonebot_plugin_qguard.services.member_role_service import MemberRoleService
from nonebot_plugin_support_bot.models import init_db as init_support_db
from nonebot_plugin_support_bot.qguard_registry import get_qguard_descriptor as get_support_descriptor


class FakeOps:
    def __init__(self, role: str = "member") -> None:
        self.role = role

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        return {"user_id": user_id, "role": self.role}


def _register_test_descriptors() -> None:
    clear_registry()
    register_plugin(get_qguard_descriptor())
    register_plugin(get_ai_descriptor())
    register_plugin(get_wiki_descriptor())
    register_plugin(get_support_descriptor())
    register_plugin(get_qfun_descriptor())


def test_registry_help_filters_by_role() -> None:
    _register_test_descriptors()

    member_help = build_help_text(QGuardRole.MEMBER)
    assert "/求助 问题描述" in member_help
    assert "/问 问题" in member_help
    assert "/娱乐 词云" in member_help
    assert "/ai状态" not in member_help
    assert "/管 禁 @用户 10m 原因" not in member_help

    super_help = build_help_text(QGuardRole.SUPER_ADMIN, include_all=True)
    assert "/ai状态" in super_help
    assert "/ai测试" in super_help
    assert "/娱乐 词云定时 开 21:30" in super_help
    assert "/管 禁 @用户 10m 原因" in super_help


def test_registry_help_can_filter_plugin_commands() -> None:
    _register_test_descriptors()

    support_help = build_help_text(QGuardRole.GROUP_ADMIN, query="客服")

    assert "/客服 状态" in support_help
    assert "/客服 模式 智能监听" in support_help
    assert "/ai状态" not in support_help


def test_registry_plugin_detail_help() -> None:
    _register_test_descriptors()

    detail = build_plugin_help_text("qinex_answer", QGuardRole.GROUP_ADMIN)

    assert "QInEX 智能问答" in detail
    assert "/求助 问题描述" in detail
    assert "/客服 开启" in detail


async def test_plugin_permission_override_affects_dynamic_help() -> None:
    _register_test_descriptors()
    group_id = 880100001

    result = await PluginCenterService().set_plugin_permission(
        group_id=group_id,
        operator_id=1348984838,
        plugin_id="qinex_answer",
        selector="/客服",
        role_text="群主",
    )

    assert result.success
    admin_help = await build_help_text_for_context(
        RegistryContext(group_id=group_id, user_id=1, role=QGuardRole.GROUP_ADMIN),
        query="客服",
    )
    owner_help = await build_help_text_for_context(
        RegistryContext(group_id=group_id, user_id=1, role=QGuardRole.GROUP_OWNER),
        query="客服",
    )
    assert "/客服 状态" not in admin_help
    assert "/客服 状态" in owner_help


async def test_plugin_center_can_toggle_support_bot_and_hide_help() -> None:
    _register_test_descriptors()
    await init_support_db()
    group_id = 880100002

    result = await PluginCenterService().set_plugin_enabled(
        group_id=group_id,
        operator_id=1348984838,
        plugin_id="qinex_answer",
        enabled=False,
    )

    assert result.success
    help_text = await build_help_text_for_context(
        RegistryContext(group_id=group_id, user_id=1, role=QGuardRole.GROUP_ADMIN),
        query="客服",
    )
    assert "/客服 状态" not in help_text


async def test_plugin_permission_override_blocks_command_execution() -> None:
    _register_test_descriptors()
    group_id = 880200000 + (uuid4().int % 100000000)

    result = await PluginCenterService().set_plugin_permission(
        group_id=group_id,
        operator_id=1348984838,
        plugin_id="qinex_answer",
        selector="/客服",
        role_text="群主",
    )

    assert result.success
    denied = await RegisteredCommandPermissionService().check(
        FakeOps(role="admin"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="qinex_answer",
        selector="/客服 状态",
        fallback_role=QGuardRole.MEMBER,
    )
    allowed = await RegisteredCommandPermissionService().check(
        FakeOps(role="owner"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="qinex_answer",
        selector="/客服 状态",
        fallback_role=QGuardRole.MEMBER,
    )

    assert not denied.allowed
    assert denied.required_role == QGuardRole.GROUP_OWNER
    assert allowed.allowed


async def test_generic_plugin_center_toggle_blocks_registered_commands() -> None:
    _register_test_descriptors()
    group_id = 880300000 + (uuid4().int % 100000000)

    result = await PluginCenterService().set_plugin_enabled(
        group_id=group_id,
        operator_id=1348984838,
        plugin_id="group_wiki",
        enabled=False,
    )

    assert result.success
    decision = await RegisteredCommandPermissionService().check(
        FakeOps(role="owner"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="group_wiki",
        selector="/知识 搜索",
        fallback_role=QGuardRole.MEMBER,
    )
    assert not decision.allowed
    assert "已在本群关闭" in decision.reason


async def test_qguard_registered_roles_match_command_execution_matrix() -> None:
    _register_test_descriptors()
    group_id = 880400000 + (uuid4().int % 100000000)
    trusted_id = 30001 + (uuid4().int % 100000)
    mini_id = 40001 + (uuid4().int % 100000)
    await MemberRoleService().set_role(group_id, 1348984838, trusted_id, QGuardRole.TRUSTED)
    await MemberRoleService().set_role(group_id, 1348984838, mini_id, QGuardRole.MINI_ADMIN)

    trusted_list = await RegisteredCommandPermissionService().check(
        FakeOps(role="member"),
        group_id=group_id,
        operator_id=trusted_id,
        plugin_id="qguard",
        selector="/管 广告词 列表",
        fallback_role=QGuardRole.TRUSTED,
    )
    mini_mute = await RegisteredCommandPermissionService().check(
        FakeOps(role="member"),
        group_id=group_id,
        operator_id=mini_id,
        plugin_id="qguard",
        selector="/管 禁 @用户 10m 原因",
        fallback_role=QGuardRole.MINI_ADMIN,
    )
    admin_newbie = await RegisteredCommandPermissionService().check(
        FakeOps(role="admin"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="qguard",
        selector="/管 新人保护 开",
        fallback_role=QGuardRole.GROUP_ADMIN,
    )
    admin_auto_patrol = await RegisteredCommandPermissionService().check(
        FakeOps(role="admin"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="qguard",
        selector="/管 自动巡检 开",
        fallback_role=QGuardRole.GROUP_ADMIN,
    )
    admin_kick_black = await RegisteredCommandPermissionService().check(
        FakeOps(role="admin"),
        group_id=group_id,
        operator_id=12345,
        plugin_id="qguard",
        selector="/管 踢黑 @用户 原因",
        fallback_role=QGuardRole.GROUP_OWNER,
    )

    assert trusted_list.allowed
    assert mini_mute.allowed
    assert admin_newbie.allowed
    assert admin_auto_patrol.allowed
    assert not admin_kick_black.allowed
    assert admin_kick_black.required_role == QGuardRole.GROUP_OWNER
