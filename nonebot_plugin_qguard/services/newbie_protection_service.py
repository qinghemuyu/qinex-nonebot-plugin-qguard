from datetime import datetime

from nonebot.adapters.onebot.v11 import GroupMessageEvent

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.punishment_service import PunishmentService


class NewbieProtectionService:
    async def record_join(self, group_id: int, user_id: int) -> None:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            seconds = config.newbie_protection_seconds if config.enabled and config.new_member_protection_enabled else 0
            await MemberRepo(session).mark_joined(group_id, user_id, seconds)
            await session.commit()

    async def handle_message(self, ops: GroupOps, operator_id: int, event: GroupMessageEvent) -> bool:
        plain_text = event.get_plaintext()
        image_count = sum(1 for segment in event.message if segment.type == "image")
        link_count = plain_text.count("http://") + plain_text.count("https://")

        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(event.group_id)
            await MemberRepo(session).touch_active(event.group_id, event.user_id)

            if not config.enabled or not config.new_member_protection_enabled:
                await session.commit()
                return False

            profile = await MemberRepo(session).get(event.group_id, event.user_id)
            if profile is None or profile.newbie_until is None or profile.newbie_until <= datetime.utcnow():
                await session.commit()
                return False

            if await PermissionService(session).is_protected_from_auto_action(ops, event.group_id, event.user_id):
                await session.commit()
                return False

            reasons: list[str] = []
            if config.newbie_block_links and link_count > 0:
                reasons.append("链接")
            if config.newbie_block_images and image_count > 0:
                reasons.append("图片")
            if not reasons:
                await session.commit()
                return False

            reason = f"新人保护：禁止新人发送{'、'.join(reasons)}。"
            mute_seconds = config.default_mute_seconds
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=operator_id,
                target_user_id=event.user_id,
                action=AuditAction.NEWBIE_PROTECTION_HIT,
                result=AuditResult.SUCCESS,
                reason=reason,
                related_message_id=event.message_id,
                metadata={"link_count": link_count, "image_count": image_count, "mute_seconds": mute_seconds},
            )
            await session.commit()

        service = PunishmentService()
        delete_result = await service.delete_msg(ops, event.group_id, operator_id, event.message_id, reason)
        mute_result = await service.mute(ops, event.group_id, operator_id, event.user_id, mute_seconds, reason, event.message_id)
        return delete_result.success or mute_result.success
