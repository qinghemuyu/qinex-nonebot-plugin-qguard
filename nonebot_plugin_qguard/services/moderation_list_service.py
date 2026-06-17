from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.blacklist_repo import BlacklistRepo
from nonebot_plugin_qguard.repositories.whitelist_repo import WhitelistRepo
from nonebot_plugin_qguard.services.result import ActionResult


class ModerationListService:
    async def add_whitelist(self, group_id: int, operator_id: int, user_id: int, reason: str | None = None) -> ActionResult:
        async with get_session() as session:
            await WhitelistRepo(session).add(group_id, user_id, operator_id, reason)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=AuditAction.ADD_WHITELIST,
                result=AuditResult.SUCCESS,
                reason=reason,
            )
            await session.commit()
        return ActionResult(success=True, action=str(AuditAction.ADD_WHITELIST), message=f"已加入白名单：{user_id}")

    async def remove_whitelist(self, group_id: int, operator_id: int, user_id: int) -> ActionResult:
        async with get_session() as session:
            removed = await WhitelistRepo(session).remove(group_id, user_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=AuditAction.REMOVE_WHITELIST,
                result=AuditResult.SUCCESS if removed else AuditResult.SKIPPED,
            )
            await session.commit()
        return ActionResult(
            success=removed,
            action=str(AuditAction.REMOVE_WHITELIST),
            message="已移出白名单。" if removed else "此用户不在白名单。",
        )

    async def list_whitelist(self, group_id: int) -> list[tuple[int, str]]:
        async with get_session() as session:
            items = await WhitelistRepo(session).list_group(group_id)
        return [(item.user_id, item.reason or "") for item in items]

    async def add_blacklist(self, group_id: int | None, operator_id: int, user_id: int, reason: str | None = None) -> ActionResult:
        async with get_session() as session:
            await BlacklistRepo(session).add(group_id, user_id, operator_id, reason)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=AuditAction.ADD_BLACKLIST,
                result=AuditResult.SUCCESS,
                reason=reason,
            )
            await session.commit()
        scope = "全局黑名单" if group_id is None else "黑名单"
        return ActionResult(success=True, action=str(AuditAction.ADD_BLACKLIST), message=f"已加入{scope}：{user_id}")

    async def remove_blacklist(self, group_id: int | None, operator_id: int, user_id: int) -> ActionResult:
        async with get_session() as session:
            removed = await BlacklistRepo(session).remove(group_id, user_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=user_id,
                action=AuditAction.REMOVE_BLACKLIST,
                result=AuditResult.SUCCESS if removed else AuditResult.SKIPPED,
            )
            await session.commit()
        return ActionResult(
            success=removed,
            action=str(AuditAction.REMOVE_BLACKLIST),
            message="已移出黑名单。" if removed else "此用户不在黑名单。",
        )

    async def list_blacklist(self, group_id: int) -> list[tuple[int, str]]:
        async with get_session() as session:
            items = await BlacklistRepo(session).list_group(group_id)
        return [(item.user_id, item.reason or "") for item in items]

    async def list_global_blacklist(self) -> list[tuple[int, str]]:
        async with get_session() as session:
            items = await BlacklistRepo(session).list_global()
        return [(item.user_id, item.reason or "") for item in items]
