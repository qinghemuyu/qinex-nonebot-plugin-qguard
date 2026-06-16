import asyncio
from dataclasses import dataclass

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.constants import (
    CARD_LOCK_EVENT_IGNORE_SECONDS,
    CARD_LOCK_GROUP_RATE_LIMIT_SECONDS,
    CARD_LOCK_MAX_FAILURES,
    CARD_LOCK_MAX_FIX_PER_SCAN,
)
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.models.card_lock import CardLock
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.card_lock_repo import CardLockRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.result import ActionResult
from nonebot_plugin_qguard.utils.locks import get_member_lock, mark_plugin_fixed, should_ignore_card_event


@dataclass(frozen=True)
class CardScanResult:
    scanned: int
    fixed: int
    failed: int
    mismatched: int


class CardLockService:
    async def lock_card(
        self,
        ops: GroupOps,
        group_id: int,
        operator_id: int,
        target_user_id: int,
        locked_card: str,
    ) -> ActionResult:
        async with get_session() as session:
            decision = await PermissionService(session).can_operate(
                ops,
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                required_role=QGuardRole.GROUP_OWNER,
            )
            if not decision.allowed:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.LOCK_CARD,
                    result=AuditResult.SKIPPED,
                    error_message=decision.reason,
                )
                await session.commit()
                return ActionResult(success=False, action="lock_card", message=decision.reason, error=decision.reason)
            try:
                await ops.set_group_card(group_id, target_user_id, locked_card)
                await CardLockRepo(session).upsert(group_id, target_user_id, locked_card, operator_id)
                mark_plugin_fixed(group_id, target_user_id, CARD_LOCK_EVENT_IGNORE_SECONDS)
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.LOCK_CARD,
                    result=AuditResult.SUCCESS,
                    metadata={"locked_card": locked_card},
                )
                await session.commit()
                return ActionResult(success=True, action="lock_card", message="名片已锁定。")
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=target_user_id,
                    action=AuditAction.LOCK_CARD,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                )
                await session.commit()
                return ActionResult(success=False, action="lock_card", message="锁定失败：机器人权限不足或 OneBot 调用失败。", error=str(exc))

    async def unlock_card(self, group_id: int, operator_id: int, target_user_id: int) -> ActionResult:
        async with get_session() as session:
            item = await CardLockRepo(session).disable(group_id, target_user_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                target_user_id=target_user_id,
                action=AuditAction.UNLOCK_CARD,
                result=AuditResult.SUCCESS if item else AuditResult.SKIPPED,
            )
            await session.commit()
            if item is None:
                return ActionResult(success=False, action="unlock_card", message="该用户没有启用中的名片锁。")
            return ActionResult(success=True, action="unlock_card", message="名片锁已解除。")

    async def list_locks(self, group_id: int, limit: int = 20) -> list[CardLock]:
        async with get_session() as session:
            return await CardLockRepo(session).list_enabled(group_id, limit)

    async def repair_member(
        self,
        ops: GroupOps,
        group_id: int,
        user_id: int,
        operator_id: int | None = None,
        current_card: str | None = None,
        from_event: bool = False,
    ) -> bool:
        if from_event and should_ignore_card_event(group_id, user_id):
            return False
        lock = get_member_lock(group_id, user_id)
        async with lock:
            async with get_session() as session:
                config = await GroupConfigRepo(session).get_or_create(group_id)
                if not config.enabled or not config.card_lock_enabled:
                    return False
                item = await CardLockRepo(session).get(group_id, user_id)
                if item is None or not item.enabled:
                    return False
                if item.failure_count >= CARD_LOCK_MAX_FAILURES:
                    return False
                if current_card is None:
                    info = await ops.get_group_member_info(group_id, user_id)
                    current_card = str(info.get("card") or "")
                if current_card == item.locked_card:
                    await CardLockRepo(session).mark_seen(item, current_card)
                    await session.commit()
                    return False
                try:
                    await ops.set_group_card(group_id, user_id, item.locked_card)
                    mark_plugin_fixed(group_id, user_id, CARD_LOCK_EVENT_IGNORE_SECONDS)
                    await CardLockRepo(session).mark_fixed(item, current_card)
                    await AuditLogRepo(session).create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.FIX_CARD,
                        result=AuditResult.SUCCESS,
                        metadata={"from": current_card, "to": item.locked_card},
                    )
                    await session.commit()
                    return True
                except Exception as exc:
                    await CardLockRepo(session).mark_failed(item, current_card, str(exc))
                    await AuditLogRepo(session).create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.FIX_CARD,
                        result=AuditResult.FAILED,
                        error_message=str(exc),
                        metadata={"from": current_card, "to": item.locked_card},
                    )
                    await session.commit()
                    return False

    async def scan_group(self, ops: GroupOps, group_id: int, operator_id: int | None = None, fix: bool = False) -> CardScanResult:
        members = await ops.get_group_member_list(group_id)
        cards = {int(item["user_id"]): str(item.get("card") or "") for item in members if "user_id" in item}
        async with get_session() as session:
            locks = await CardLockRepo(session).list_enabled(group_id, limit=1000)
        scanned = 0
        fixed = 0
        failed = 0
        mismatched = 0
        for item in locks:
            scanned += 1
            current_card = cards.get(item.user_id, "")
            if current_card == item.locked_card:
                continue
            mismatched += 1
            if not fix or fixed >= CARD_LOCK_MAX_FIX_PER_SCAN:
                continue
            ok = await self.repair_member(ops, group_id, item.user_id, operator_id, current_card)
            if ok:
                fixed += 1
                await asyncio.sleep(CARD_LOCK_GROUP_RATE_LIMIT_SECONDS)
            else:
                failed += 1
        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SCAN_CARD,
                result=AuditResult.SUCCESS,
                metadata={"scanned": scanned, "mismatched": mismatched, "fixed": fixed, "failed": failed},
            )
            await session.commit()
        return CardScanResult(scanned=scanned, mismatched=mismatched, fixed=fixed, failed=failed)
