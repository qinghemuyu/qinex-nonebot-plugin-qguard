from dataclasses import dataclass

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.group_setting_service import GroupSettingService


@dataclass(frozen=True)
class PatrolResult:
    checked: int = 0
    fixed: int = 0
    failed: int = 0
    message: str = ""


class PatrolService:
    async def patrol_all(self, ops: GroupOps, group_id: int, operator_id: int | None = None) -> PatrolResult:
        setting_result = await self.patrol_group_settings(ops, group_id, operator_id)
        card_result = await self.patrol_cards(ops, group_id, operator_id)
        checked = setting_result.checked + card_result.checked
        fixed = setting_result.fixed + card_result.fixed
        failed = setting_result.failed + card_result.failed
        message = f"巡检完成：检查 {checked} 项，修复 {fixed} 项，失败 {failed} 项。"
        await self._audit(group_id, operator_id, "all", checked, fixed, failed)
        return PatrolResult(checked=checked, fixed=fixed, failed=failed, message=message)

    async def patrol_group_settings(self, ops: GroupOps, group_id: int, operator_id: int | None = None) -> PatrolResult:
        service = GroupSettingService()
        name_result = await service.repair_group_name(ops, group_id, operator_id)
        anonymous_result = await service.repair_anonymous(ops, group_id, operator_id)
        checked = name_result.checked + anonymous_result.checked
        fixed = name_result.fixed + anonymous_result.fixed
        failed = name_result.failed + anonymous_result.failed
        message = f"群设置巡检完成：检查 {checked} 项，修复 {fixed} 项，失败 {failed} 项。"
        await self._audit(group_id, operator_id, "settings", checked, fixed, failed)
        return PatrolResult(checked=checked, fixed=fixed, failed=failed, message=message)

    async def patrol_cards(self, ops: GroupOps, group_id: int, operator_id: int | None = None) -> PatrolResult:
        result = await CardLockService().scan_group(ops, group_id, operator_id=operator_id, fix=True, force=True)
        message = f"名片巡检完成：检查 {result.scanned} 人，异常 {result.mismatched} 人，修复 {result.fixed} 人，失败 {result.failed} 人。"
        await self._audit(group_id, operator_id, "cards", result.scanned, result.fixed, result.failed)
        return PatrolResult(checked=result.scanned, fixed=result.fixed, failed=result.failed, message=message)

    async def _audit(
        self,
        group_id: int,
        operator_id: int | None,
        patrol_type: str,
        checked: int,
        fixed: int,
        failed: int,
    ) -> None:
        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.PATROL,
                result=AuditResult.SUCCESS if failed == 0 else AuditResult.FAILED,
                metadata={"type": patrol_type, "checked": checked, "fixed": fixed, "failed": failed},
            )
            await session.commit()
