from __future__ import annotations

from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.registry import (
    RegistryContext,
    get_plugin,
    parse_registry_role,
    resolve_group_enabled,
    set_group_enabled,
)
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_plugin_config_repo import GroupPluginConfigRepo
from nonebot_plugin_qguard.services.member_role_service import ROLE_LABELS
from nonebot_plugin_qguard.services.result import ActionResult


class PluginCenterService:
    async def configs_for_group(self, group_id: int):
        async with get_session() as session:
            items = await GroupPluginConfigRepo(session).list_by_group(group_id)
            return {item.plugin_id: item for item in items}

    async def set_plugin_enabled(
        self,
        *,
        group_id: int,
        operator_id: int,
        plugin_id: str,
        enabled: bool,
    ) -> ActionResult:
        plugin = get_plugin(plugin_id)
        if plugin is None:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_PLUGIN_ENABLED),
                message=f"没有找到插件：{plugin_id}",
            )

        context = RegistryContext(group_id=group_id, user_id=operator_id, role=QGuardRole.SUPER_ADMIN)
        if plugin.group_enable_setter is None:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_PLUGIN_ENABLED),
                message=f"{plugin.display_name} 暂不支持通过插件中心开关。",
            )

        message = await set_group_enabled(plugin, context, enabled)
        async with get_session() as session:
            await GroupPluginConfigRepo(session).set_enabled(group_id, plugin_id, enabled, operator_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_PLUGIN_ENABLED,
                result=AuditResult.SUCCESS,
                metadata={"plugin_id": plugin_id, "enabled": enabled},
            )
            await session.commit()

        state = await resolve_group_enabled(plugin, context)
        suffix = "" if state is None else f"（当前 {'开' if state else '关'}）"
        return ActionResult(
            success=True,
            action=str(AuditAction.SET_PLUGIN_ENABLED),
            message=message or f"{plugin.display_name} 已{'开启' if enabled else '关闭'}。{suffix}",
        )

    async def set_plugin_permission(
        self,
        *,
        group_id: int,
        operator_id: int,
        plugin_id: str,
        selector: str,
        role_text: str,
    ) -> ActionResult:
        plugin = get_plugin(plugin_id)
        if plugin is None:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_PLUGIN_PERMISSION),
                message=f"没有找到插件：{plugin_id}",
            )

        try:
            role = parse_registry_role(role_text)
        except ValueError as exc:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_PLUGIN_PERMISSION),
                message=str(exc),
            )

        matches = _match_commands(plugin.commands, selector)
        if not matches:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_PLUGIN_PERMISSION),
                message=f"{plugin.display_name} 没有匹配命令：{selector}",
            )

        async with get_session() as session:
            repo = GroupPluginConfigRepo(session)
            item = await repo.get_or_create(group_id, plugin_id)
            overrides = repo.permission_overrides(item)
            for command in matches:
                overrides[command.usage] = int(role)
            await repo.set_permission_overrides(group_id, plugin_id, overrides, operator_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_PLUGIN_PERMISSION,
                result=AuditResult.SUCCESS,
                metadata={
                    "plugin_id": plugin_id,
                    "selector": selector,
                    "matched": [command.usage for command in matches],
                    "role": int(role),
                },
            )
            await session.commit()

        role_label = ROLE_LABELS.get(role, str(role))
        return ActionResult(
            success=True,
            action=str(AuditAction.SET_PLUGIN_PERMISSION),
            message=f"{plugin.display_name} 已设置 {len(matches)} 条命令权限为：{role_label}+。",
        )

    async def record_status_query(self, group_id: int, operator_id: int, plugin_id: str | None = None) -> None:
        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.QUERY_PLUGIN_STATUS,
                result=AuditResult.SUCCESS,
                metadata={"plugin_id": plugin_id},
            )
            await session.commit()


def _match_commands(commands, selector: str):
    normalized = selector.strip()
    if not normalized:
        return []
    matches = []
    for command in commands:
        if command.usage == normalized or command.command == normalized or command.usage.startswith(f"{normalized} "):
            matches.append(command)
    return matches
