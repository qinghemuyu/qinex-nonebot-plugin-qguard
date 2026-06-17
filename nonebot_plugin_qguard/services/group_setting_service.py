from dataclasses import dataclass

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.result import ActionResult


@dataclass(frozen=True)
class RepairResult:
    checked: int = 0
    fixed: int = 0
    failed: int = 0
    message: str = ""


class GroupSettingService:
    async def set_whole_mute(self, ops: GroupOps, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            try:
                await ops.whole_mute(group_id, enabled)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_WHOLE_MUTE,
                    result=AuditResult.SUCCESS,
                    metadata={"whole_mute_enabled": enabled},
                )
                await session.commit()
                return ActionResult(
                    success=True,
                    action=str(AuditAction.SET_WHOLE_MUTE),
                    message=f"全体禁言已{'开启' if enabled else '关闭'}。",
                )
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_WHOLE_MUTE,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"whole_mute_enabled": enabled},
                )
                await session.commit()
                return ActionResult(
                    success=False,
                    action=str(AuditAction.SET_WHOLE_MUTE),
                    message="全体禁言设置失败。",
                    error=str(exc),
                )

    async def set_group_name(self, ops: GroupOps, group_id: int, operator_id: int, name: str) -> ActionResult:
        name = name.strip()
        if not name:
            return ActionResult(success=False, action=str(AuditAction.SET_GROUP_NAME), message="群名不能为空。")

        async with get_session() as session:
            try:
                await ops.set_group_name(group_id, name)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_GROUP_NAME,
                    result=AuditResult.SUCCESS,
                    metadata={"group_name": name},
                )
                await session.commit()
                return ActionResult(success=True, action=str(AuditAction.SET_GROUP_NAME), message="群名已设置。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_GROUP_NAME,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"group_name": name},
                )
                await session.commit()
                return ActionResult(success=False, action=str(AuditAction.SET_GROUP_NAME), message="群名设置失败。", error=str(exc))

    async def lock_group_name(self, ops: GroupOps, group_id: int, operator_id: int, name: str) -> ActionResult:
        name = name.strip()
        if not name:
            return ActionResult(success=False, action=str(AuditAction.LOCK_GROUP_NAME), message="锁定群名不能为空。")

        async with get_session() as session:
            await GroupConfigRepo(session).set_group_name_lock(group_id, True, name)
            try:
                await ops.set_group_name(group_id, name)
                result = AuditResult.SUCCESS
                error = None
                message = "群名锁已开启。"
            except Exception as exc:
                result = AuditResult.FAILED
                error = str(exc)
                message = "群名锁已保存，但设置群名失败。"
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.LOCK_GROUP_NAME,
                result=result,
                error_message=error,
                metadata={"group_name": name},
            )
            await session.commit()
        return ActionResult(success=error is None, action=str(AuditAction.LOCK_GROUP_NAME), message=message, error=error)

    async def unlock_group_name(self, group_id: int, operator_id: int) -> ActionResult:
        async with get_session() as session:
            await GroupConfigRepo(session).set_group_name_lock(group_id, False)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.UNLOCK_GROUP_NAME,
                result=AuditResult.SUCCESS,
            )
            await session.commit()
        return ActionResult(success=True, action=str(AuditAction.UNLOCK_GROUP_NAME), message="群名锁已关闭。")

    async def repair_group_name(self, ops: GroupOps, group_id: int, operator_id: int | None = None) -> RepairResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            if not config.group_name_lock_enabled or not config.locked_group_name.strip():
                await session.commit()
                return RepairResult(message="群名锁未开启。")
            target_name = config.locked_group_name.strip()

        try:
            info = await ops.get_group_info(group_id, no_cache=True)
            current_name = str(info.get("group_name") or "")
            if current_name == target_name:
                return RepairResult(checked=1, message="群名正常。")
            await ops.set_group_name(group_id, target_name)
            async with get_session() as session:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.FIX_GROUP_NAME,
                    result=AuditResult.SUCCESS,
                    metadata={"old_group_name": current_name, "group_name": target_name},
                )
                await session.commit()
            return RepairResult(checked=1, fixed=1, message="群名已修复。")
        except Exception as exc:
            async with get_session() as session:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.FIX_GROUP_NAME,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                )
                await session.commit()
            return RepairResult(checked=1, failed=1, message=f"群名修复失败：{exc}")

    async def set_anonymous(self, ops: GroupOps, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            try:
                await ops.set_group_anonymous(group_id, enabled)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_ANONYMOUS,
                    result=AuditResult.SUCCESS,
                    metadata={"anonymous_enabled": enabled},
                )
                await session.commit()
                return ActionResult(success=True, action=str(AuditAction.SET_ANONYMOUS), message=f"匿名已{'开启' if enabled else '关闭'}。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.SET_ANONYMOUS,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"anonymous_enabled": enabled},
                )
                await session.commit()
                return ActionResult(success=False, action=str(AuditAction.SET_ANONYMOUS), message="匿名设置失败。", error=str(exc))

    async def lock_anonymous(self, ops: GroupOps, group_id: int, operator_id: int, desired_enabled: bool) -> ActionResult:
        async with get_session() as session:
            await GroupConfigRepo(session).set_anonymous_lock(group_id, True, desired_enabled)
            try:
                await ops.set_group_anonymous(group_id, desired_enabled)
                result = AuditResult.SUCCESS
                error = None
                message = f"匿名锁已开启，目标状态：{'开' if desired_enabled else '关'}。"
            except Exception as exc:
                result = AuditResult.FAILED
                error = str(exc)
                message = "匿名锁已保存，但设置匿名状态失败。"
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.LOCK_ANONYMOUS,
                result=result,
                error_message=error,
                metadata={"anonymous_enabled": desired_enabled},
            )
            await session.commit()
        return ActionResult(success=error is None, action=str(AuditAction.LOCK_ANONYMOUS), message=message, error=error)

    async def unlock_anonymous(self, group_id: int, operator_id: int) -> ActionResult:
        async with get_session() as session:
            await GroupConfigRepo(session).set_anonymous_lock(group_id, False)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.UNLOCK_ANONYMOUS,
                result=AuditResult.SUCCESS,
            )
            await session.commit()
        return ActionResult(success=True, action=str(AuditAction.UNLOCK_ANONYMOUS), message="匿名锁已关闭。")

    async def repair_anonymous(self, ops: GroupOps, group_id: int, operator_id: int | None = None) -> RepairResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            if not config.anonymous_lock_enabled:
                await session.commit()
                return RepairResult(message="匿名锁未开启。")
            desired_enabled = config.anonymous_enabled

        try:
            await ops.set_group_anonymous(group_id, desired_enabled)
            async with get_session() as session:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.LOCK_ANONYMOUS,
                    result=AuditResult.SUCCESS,
                    metadata={"anonymous_enabled": desired_enabled, "repair": True},
                )
                await session.commit()
            return RepairResult(checked=1, fixed=1, message="匿名状态已按锁定值重设。")
        except Exception as exc:
            async with get_session() as session:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    action=AuditAction.LOCK_ANONYMOUS,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"anonymous_enabled": desired_enabled, "repair": True},
                )
                await session.commit()
            return RepairResult(checked=1, failed=1, message=f"匿名状态修复失败：{exc}")

    async def set_special_title(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        user_id: int,
        title: str,
        bot_user_id: int | None = None,
    ) -> ActionResult:
        title = title.strip()
        async with get_session() as session:
            if bot_user_id is not None:
                try:
                    bot_info = await ops.get_group_member_info(group_id, bot_user_id, no_cache=True)
                except Exception as exc:
                    await AuditLogRepo(session).create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.SET_SPECIAL_TITLE,
                        result=AuditResult.FAILED,
                        error_message=str(exc),
                        metadata={"title": title, "check_bot_role": True},
                    )
                    await session.commit()
                    return ActionResult(
                        success=False,
                        action=str(AuditAction.SET_SPECIAL_TITLE),
                        message=f"查询机器人群身份失败，无法确认能否设置头衔：{exc}",
                        error=str(exc),
                    )

                bot_role = str(bot_info.get("role") or "")
                if bot_role != "owner":
                    reason = f"专属头衔只有群主能设置，机器人当前角色是 {bot_role or '未知'}。"
                    await AuditLogRepo(session).create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.SET_SPECIAL_TITLE,
                        result=AuditResult.SKIPPED,
                        reason=reason,
                        metadata={"title": title, "bot_role": bot_role},
                    )
                    await session.commit()
                    return ActionResult(
                        success=False,
                        action=str(AuditAction.SET_SPECIAL_TITLE),
                        message=reason,
                        error=reason,
                    )

            try:
                await ops.set_special_title(group_id, user_id, title)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=user_id,
                    action=AuditAction.SET_SPECIAL_TITLE,
                    result=AuditResult.SUCCESS,
                    metadata={"title": title},
                )
                await session.commit()
                return ActionResult(success=True, action=str(AuditAction.SET_SPECIAL_TITLE), message="专属头衔已设置。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=user_id,
                    action=AuditAction.SET_SPECIAL_TITLE,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"title": title},
                )
                await session.commit()
                return ActionResult(success=False, action=str(AuditAction.SET_SPECIAL_TITLE), message="专属头衔设置失败。", error=str(exc))
