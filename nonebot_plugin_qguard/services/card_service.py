from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.result import ActionResult
from nonebot_plugin_qguard.utils.message_parser import display_member_name


class CardService:
    async def set_card(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        target_user_id: int,
        card: str,
    ) -> ActionResult:
        action = AuditAction.CLEAR_CARD if card == "" else AuditAction.SET_CARD
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops,
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                required_role=QGuardRole.GROUP_ADMIN,
            )
            if not decision.allowed:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=action,
                    result=AuditResult.SKIPPED,
                    error_message=decision.reason,
                )
                await session.commit()
                return ActionResult(success=False, action=str(action), message=decision.reason, error=decision.reason)
            try:
                await ops.set_group_card(group_id, target_user_id, card)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=action,
                    result=AuditResult.SUCCESS,
                    metadata={"card": card},
                )
                await session.commit()
                return ActionResult(success=True, action=str(action), message="名片已更新。" if card else "名片已清空。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=action,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"card": card},
                )
                await session.commit()
                return ActionResult(success=False, action=str(action), message="操作失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))

    async def query_card(self, ops: GroupOps, group_id: int, user_id: int) -> ActionResult:
        try:
            info = await ops.get_group_member_info(group_id, user_id)
        except Exception as exc:
            return ActionResult(success=False, action="query_card", message="查询失败。", error=str(exc))
        card = str(info.get("card") or "")
        name = display_member_name(info)
        text = f"用户：{user_id}\n展示名：{name}\n群名片：{card or '空'}"
        return ActionResult(success=True, action="query_card", message=text)
