from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo
from nonebot_plugin_qguard.services.result import ActionResult


ROLE_LABELS = {
    QGuardRole.MEMBER: "普通成员",
    QGuardRole.TRUSTED: "可信用户",
    QGuardRole.MINI_ADMIN: "小管理",
    QGuardRole.GROUP_ADMIN: "群管理员",
    QGuardRole.GROUP_OWNER: "群主",
    QGuardRole.SUPER_ADMIN: "超级管理员",
}


def parse_plugin_role(text: str) -> QGuardRole:
    aliases = {
        "普通": QGuardRole.MEMBER,
        "成员": QGuardRole.MEMBER,
        "普通成员": QGuardRole.MEMBER,
        "可信": QGuardRole.TRUSTED,
        "可信用户": QGuardRole.TRUSTED,
        "信任": QGuardRole.TRUSTED,
        "小管理": QGuardRole.MINI_ADMIN,
        "小管": QGuardRole.MINI_ADMIN,
        "mini": QGuardRole.MINI_ADMIN,
    }
    if text not in aliases:
        raise ValueError("角色只支持：普通、可信、小管理。")
    return aliases[text]


class MemberRoleService:
    async def set_role(self, group_id: int, operator_id: int, target_user_id: int, role: QGuardRole) -> ActionResult:
        async with get_session() as session:
            profile = await MemberRepo(session).set_role(group_id, target_user_id, role)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                action=AuditAction.SET_MEMBER_ROLE,
                result=AuditResult.SUCCESS,
                metadata={"role": int(role), "role_name": ROLE_LABELS[role]},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_MEMBER_ROLE),
                message=f"{profile.user_id} 已设置为{ROLE_LABELS[role]}。",
            )

    async def get_plugin_role(self, group_id: int, user_id: int) -> QGuardRole:
        async with get_session() as session:
            profile = await MemberRepo(session).get(group_id, user_id)
            if profile is None:
                return QGuardRole.MEMBER
            return QGuardRole(profile.role)
