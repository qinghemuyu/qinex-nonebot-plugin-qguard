from nonebot_plugin_ai_core.qguard_registry import get_qguard_descriptor as get_ai_descriptor
from nonebot_plugin_group_wiki.qguard_registry import get_qguard_descriptor as get_wiki_descriptor
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
from nonebot_plugin_qguard.services.plugin_center_service import PluginCenterService
from nonebot_plugin_support_bot.models import init_db as init_support_db
from nonebot_plugin_support_bot.qguard_registry import get_qguard_descriptor as get_support_descriptor


def _register_test_descriptors() -> None:
    clear_registry()
    register_plugin(get_qguard_descriptor())
    register_plugin(get_ai_descriptor())
    register_plugin(get_wiki_descriptor())
    register_plugin(get_support_descriptor())


def test_registry_help_filters_by_role() -> None:
    _register_test_descriptors()

    member_help = build_help_text(QGuardRole.MEMBER)
    assert "/求助 问题描述" in member_help
    assert "/问 问题" in member_help
    assert "/ai状态" not in member_help
    assert "/管 禁 @用户 10m 原因" not in member_help

    super_help = build_help_text(QGuardRole.SUPER_ADMIN, include_all=True)
    assert "/ai状态" in super_help
    assert "/ai测试" in super_help
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
