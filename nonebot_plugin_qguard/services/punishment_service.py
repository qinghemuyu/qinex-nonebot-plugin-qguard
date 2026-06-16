from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.constants import DEFAULT_REASON
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.result import ActionResult
from nonebot_plugin_qguard.utils.cqcode import at


class PunishmentService:
    async def _check_enabled(self, session, group_id: int) -> bool:
        config = await GroupConfigRepo(session).get_or_create(group_id)
        return config.enabled

    async def _deny(self, session, action: AuditAction, group_id: int, operator_id: int, target_user_id: int | None, reason: str) -> ActionResult:
        await AuditLogRepo(session).create(
            group_id=group_id,
            operator_id=operator_id,
            target_user_id=target_user_id,
            action=action,
            result=AuditResult.SKIPPED,
            error_message=reason,
        )
        return ActionResult(success=False, action=str(action), message=reason, error=reason)

    async def warn(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        target_user_id: int,
        reason: str = DEFAULT_REASON,
        related_message_id: int | None = None,
    ) -> ActionResult:
        async with get_session() as session:
            if not await self._check_enabled(session, group_id):
                result = await self._deny(session, AuditAction.WARN, group_id, operator_id, target_user_id, "本群 QGuard 未开启。")
                await session.commit()
                return result
            decision = await PermissionService(session).can_operate(
                ops, group_id=group_id, operator_id=operator_id, target_user_id=target_user_id
            )
            if not decision.allowed:
                result = await self._deny(session, AuditAction.WARN, group_id, operator_id, target_user_id, decision.reason)
                await session.commit()
                return result
            await MemberRepo(session).add_warning(group_id, target_user_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                action=AuditAction.WARN,
                result=AuditResult.SUCCESS,
                reason=reason,
                related_message_id=related_message_id,
            )
            await session.commit()
        await ops.send_group_msg(group_id, f"{at(target_user_id)} 警告：{reason}")
        return ActionResult(success=True, action="warn", message="已警告。")

    async def mute(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        target_user_id: int,
        seconds: int,
        reason: str = DEFAULT_REASON,
        related_message_id: int | None = None,
    ) -> ActionResult:
        async with get_session() as session:
            if not await self._check_enabled(session, group_id):
                result = await self._deny(session, AuditAction.MUTE, group_id, operator_id, target_user_id, "本群 QGuard 未开启。")
                await session.commit()
                return result
            decision = await PermissionService(session).can_operate(
                ops, group_id=group_id, operator_id=operator_id, target_user_id=target_user_id
            )
            if not decision.allowed:
                result = await self._deny(session, AuditAction.MUTE, group_id, operator_id, target_user_id, decision.reason)
                await session.commit()
                return result
            try:
                await ops.mute(group_id, target_user_id, seconds)
                await MemberRepo(session).add_mute(group_id, target_user_id)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.MUTE,
                    result=AuditResult.SUCCESS,
                    reason=reason,
                    related_message_id=related_message_id,
                    metadata={"seconds": seconds},
                )
                await session.commit()
                return ActionResult(success=True, action="mute", message=f"已禁言 {seconds} 秒。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.MUTE,
                    result=AuditResult.FAILED,
                    reason=reason,
                    error_message=str(exc),
                )
                await session.commit()
                return ActionResult(success=False, action="mute", message="操作失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))

    async def unmute(self, ops: GroupOps, group_id: int, operator_id: int, target_user_id: int, reason: str = DEFAULT_REASON) -> ActionResult:
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops, group_id=group_id, operator_id=operator_id, target_user_id=target_user_id
            )
            if not decision.allowed:
                result = await self._deny(session, AuditAction.UNMUTE, group_id, operator_id, target_user_id, decision.reason)
                await session.commit()
                return result
            try:
                await ops.unmute(group_id, target_user_id)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.UNMUTE,
                    result=AuditResult.SUCCESS,
                    reason=reason,
                )
                await session.commit()
                return ActionResult(success=True, action="unmute", message="已解除禁言。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.UNMUTE,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                )
                await session.commit()
                return ActionResult(success=False, action="unmute", message="操作失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))

    async def kick(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        target_user_id: int,
        reason: str = DEFAULT_REASON,
        reject_add_request: bool = False,
    ) -> ActionResult:
        action = AuditAction.KICK_BLACK if reject_add_request else AuditAction.KICK
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops,
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                required_role=QGuardRole.GROUP_ADMIN,
            )
            if not decision.allowed:
                result = await self._deny(session, action, group_id, operator_id, target_user_id, decision.reason)
                await session.commit()
                return result
            try:
                await ops.kick(group_id, target_user_id, reject_add_request)
                await MemberRepo(session).add_kick(group_id, target_user_id)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=action,
                    result=AuditResult.SUCCESS,
                    reason=reason,
                )
                await session.commit()
                return ActionResult(
                    success=True,
                    action=str(action),
                    message="已踢出。" if not reject_add_request else "已踢出并拒绝再次加群。",
                )
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=action,
                    result=AuditResult.FAILED,
                    reason=reason,
                    error_message=str(exc),
                )
                await session.commit()
                return ActionResult(success=False, action=str(action), message="操作失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))

    async def delete_msg(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        message_id: int,
        reason: str = DEFAULT_REASON,
    ) -> ActionResult:
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops, group_id=group_id, operator_id=operator_id, required_role=QGuardRole.GROUP_ADMIN
            )
            if not decision.allowed:
                result = await self._deny(session, AuditAction.DELETE_MSG, group_id, operator_id, None, decision.reason)
                await session.commit()
                return result
            try:
                await ops.delete_msg(message_id)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.DELETE_MSG,
                    result=AuditResult.SUCCESS,
                    reason=reason,
                    related_message_id=message_id,
                )
                await session.commit()
                return ActionResult(success=True, action="delete_msg", message="已撤回。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.DELETE_MSG,
                    result=AuditResult.FAILED,
                    reason=reason,
                    related_message_id=message_id,
                    error_message=str(exc),
                )
                await session.commit()
                return ActionResult(success=False, action="delete_msg", message="操作失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))
