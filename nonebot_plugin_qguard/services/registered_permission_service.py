from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.registry import (
    command_required_role,
    find_command_descriptor,
    get_plugin,
)
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_plugin_config_repo import GroupPluginConfigRepo
from nonebot_plugin_qguard.services.member_role_service import ROLE_LABELS
from nonebot_plugin_qguard.services.permission_service import PermissionService


@dataclass(frozen=True)
class RegisteredCommandDecision:
    allowed: bool
    reason: str = ""
    plugin_id: str = ""
    selector: str = ""
    command_usage: str = ""
    required_role: QGuardRole = QGuardRole.MEMBER
    operator_role: QGuardRole = QGuardRole.MEMBER
    plugin_enabled: bool = True


class RegisteredCommandPermissionService:
    async def check(
        self,
        ops: GroupOps,
        *,
        group_id: int,
        operator_id: int,
        plugin_id: str,
        selector: str,
        fallback_role: QGuardRole = QGuardRole.MEMBER,
        enforce_plugin_enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredCommandDecision:
        plugin = get_plugin(plugin_id)
        if plugin is None:
            return RegisteredCommandDecision(
                allowed=True,
                plugin_id=plugin_id,
                selector=selector,
                required_role=fallback_role,
            )

        command = find_command_descriptor(plugin, selector)

        async with get_session() as session:
            repo = GroupPluginConfigRepo(session)
            config = await repo.get(group_id, plugin_id)
            operator_role = await PermissionService(session).get_role(ops, group_id, operator_id)

            if enforce_plugin_enabled and config is not None and config.enabled is False:
                decision = RegisteredCommandDecision(
                    allowed=False,
                    reason=f"{plugin.display_name} 已在本群关闭。",
                    plugin_id=plugin_id,
                    selector=selector,
                    command_usage="" if command is None else command.usage,
                    required_role=fallback_role,
                    operator_role=operator_role,
                    plugin_enabled=False,
                )
                await self._record_denied(session, group_id, operator_id, decision, metadata)
                await session.commit()
                return decision

            overrides = {
                key: QGuardRole(value)
                for key, value in repo.permission_overrides(config).items()
                if _is_role_value(value)
            }
            required_role = command_required_role(
                command,
                permission_overrides=overrides,
                fallback_role=fallback_role,
            )
            if operator_role < required_role:
                decision = RegisteredCommandDecision(
                    allowed=False,
                    reason=f"权限不足，需要{ROLE_LABELS.get(required_role, required_role)}以上。",
                    plugin_id=plugin_id,
                    selector=selector,
                    command_usage="" if command is None else command.usage,
                    required_role=required_role,
                    operator_role=operator_role,
                )
                await self._record_denied(session, group_id, operator_id, decision, metadata)
                await session.commit()
                return decision

        return RegisteredCommandDecision(
            allowed=True,
            plugin_id=plugin_id,
            selector=selector,
            command_usage="" if command is None else command.usage,
            required_role=required_role,
            operator_role=operator_role,
        )

    async def _record_denied(
        self,
        session,
        group_id: int,
        operator_id: int,
        decision: RegisteredCommandDecision,
        metadata: dict[str, Any] | None,
    ) -> None:
        await AuditLogRepo(session).create(
            group_id=group_id,
            operator_id=operator_id,
            action=AuditAction.PERMISSION_DENIED,
            result=AuditResult.SKIPPED,
            reason=decision.reason,
            metadata={
                **(metadata or {}),
                "plugin_id": decision.plugin_id,
                "selector": decision.selector,
                "command_usage": decision.command_usage,
                "required_role": int(decision.required_role),
                "operator_role": int(decision.operator_role),
                "plugin_enabled": decision.plugin_enabled,
            },
        )


def _is_role_value(value: Any) -> bool:
    try:
        QGuardRole(value)
    except (TypeError, ValueError):
        return False
    return True
