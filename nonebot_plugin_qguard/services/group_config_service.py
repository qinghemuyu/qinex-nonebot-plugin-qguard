from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.result import ActionResult


class GroupConfigService:
    async def status(self, group_id: int):
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            await session.commit()
            return config

    async def set_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        action = AuditAction.ENABLE_GROUP if enabled else AuditAction.DISABLE_GROUP
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=action,
                result=AuditResult.SUCCESS,
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(action),
                message=f"QGuard 已{'开启' if config.enabled else '关闭'}。",
            )

    async def set_card_lock_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_card_lock_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.PATROL,
                result=AuditResult.SUCCESS,
                metadata={"card_lock_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action="set_card_lock_enabled",
                message=f"名片锁全群巡检已{'开启' if config.card_lock_enabled else '关闭'}。",
            )

    async def set_auto_delete_reply_seconds(self, group_id: int, operator_id: int, seconds: int) -> ActionResult:
        seconds = max(0, seconds)
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_auto_delete_reply_seconds(group_id, seconds)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_DELETE_REPLY,
                result=AuditResult.SUCCESS,
                metadata={"auto_delete_reply_seconds": seconds},
            )
            await session.commit()
            message = (
                "自动撤回已关闭。"
                if config.auto_delete_reply_seconds <= 0
                else f"自动撤回已设置为 {config.auto_delete_reply_seconds} 秒；机器人非管理时实际最多 110 秒。"
            )
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_DELETE_REPLY),
                message=message,
            )

    async def set_anti_ad_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_anti_ad_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_ANTI_AD,
                result=AuditResult.SUCCESS,
                metadata={"anti_ad_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_ANTI_AD),
                message=f"广告检测已{'开启' if config.anti_ad_enabled else '关闭'}。",
            )

    async def set_anti_spam_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_anti_spam_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_ANTI_SPAM,
                result=AuditResult.SUCCESS,
                metadata={"anti_spam_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_ANTI_SPAM),
                message=f"刷屏检测已{'开启' if config.anti_spam_enabled else '关闭'}。",
            )

    async def set_new_member_protection_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_new_member_protection_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_NEWBIE_PROTECTION,
                result=AuditResult.SUCCESS,
                metadata={"new_member_protection_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_NEWBIE_PROTECTION),
                message=f"新人保护已{'开启' if config.new_member_protection_enabled else '关闭'}。",
            )

    async def set_newbie_protection_seconds(self, group_id: int, operator_id: int, seconds: int) -> ActionResult:
        seconds = max(0, seconds)
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_newbie_protection_seconds(group_id, seconds)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_NEWBIE_PROTECTION_DURATION,
                result=AuditResult.SUCCESS,
                metadata={"newbie_protection_seconds": seconds},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_NEWBIE_PROTECTION_DURATION),
                message=f"新人保护时长已设置为 {config.newbie_protection_seconds} 秒。",
            )

    async def set_newbie_block_images(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_newbie_block_images(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_NEWBIE_PROTECTION_IMAGE,
                result=AuditResult.SUCCESS,
                metadata={"newbie_block_images": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_NEWBIE_PROTECTION_IMAGE),
                message=f"新人图片拦截已{'开启' if config.newbie_block_images else '关闭'}。",
            )

    async def set_auto_patrol_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_auto_patrol_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_PATROL,
                result=AuditResult.SUCCESS,
                metadata={"auto_patrol_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_PATROL),
                message=f"自动巡检已{'开启' if config.auto_patrol_enabled else '关闭'}。",
            )

    async def set_auto_patrol_interval_seconds(self, group_id: int, operator_id: int, seconds: int) -> ActionResult:
        seconds = max(5, seconds)
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_auto_patrol_interval_seconds(group_id, seconds)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_PATROL_INTERVAL,
                result=AuditResult.SUCCESS,
                metadata={"auto_patrol_interval_seconds": seconds},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_PATROL_INTERVAL),
                message=f"自动巡检间隔已设置为 {config.auto_patrol_interval_seconds} 秒。",
            )
