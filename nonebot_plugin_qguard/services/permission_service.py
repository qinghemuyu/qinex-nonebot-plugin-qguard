from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.config import load_config
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo
from nonebot_plugin_qguard.repositories.whitelist_repo import WhitelistRepo


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    operator_role: QGuardRole
    target_role: QGuardRole | None = None
    reason: str = ""


class PermissionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = load_config()

    async def get_role(
        self,
        ops: GroupOps,
        group_id: int,
        user_id: int,
        member_info: dict[str, Any] | None = None,
    ) -> QGuardRole:
        if user_id in self.config.qguard_super_admins:
            return QGuardRole.SUPER_ADMIN

        plugin_role = QGuardRole.MEMBER
        profile = await MemberRepo(self.session).get(group_id, user_id)
        if profile is not None and profile.role > int(QGuardRole.MEMBER):
            plugin_role = QGuardRole(profile.role)

        if member_info is None:
            try:
                member_info = await ops.get_group_member_info(group_id, user_id)
            except Exception:
                member_info = {}
        role = member_info.get("role")
        onebot_role = QGuardRole.MEMBER
        if role == "owner":
            onebot_role = QGuardRole.GROUP_OWNER
        elif role == "admin":
            onebot_role = QGuardRole.GROUP_ADMIN
        return max(plugin_role, onebot_role)

    async def can_operate(
        self,
        ops: GroupOps,
        *,
        group_id: int,
        operator_id: int,
        target_user_id: int | None = None,
        required_role: QGuardRole = QGuardRole.GROUP_ADMIN,
    ) -> PermissionDecision:
        operator_role = await self.get_role(ops, group_id, operator_id)
        if operator_role < required_role:
            return PermissionDecision(False, operator_role, reason="权限不足。")

        if target_user_id is None or operator_role == QGuardRole.SUPER_ADMIN:
            return PermissionDecision(True, operator_role)

        target_role = await self.get_role(ops, group_id, target_user_id)
        if target_role >= operator_role:
            return PermissionDecision(False, operator_role, target_role, "不能操作同级或更高权限的成员。")

        return PermissionDecision(True, operator_role, target_role)

    async def is_protected_from_auto_action(self, ops: GroupOps, group_id: int, user_id: int) -> bool:
        if await WhitelistRepo(self.session).is_whitelisted(group_id, user_id):
            return True
        role = await self.get_role(ops, group_id, user_id)
        return role >= QGuardRole.TRUSTED
