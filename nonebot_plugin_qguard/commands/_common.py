from typing import Any

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.config import Config, load_config
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.utils.message_parser import split_command


def get_plugin_config() -> Config:
    return load_config()


def parse_qguard_args(event: GroupMessageEvent) -> list[str]:
    config = get_plugin_config()
    return split_command(config.qguard_command_prefix, event.get_plaintext())


def make_ops(bot: Bot) -> OneBotV11GroupOps:
    return OneBotV11GroupOps(bot)


async def finish_reply(matcher: Any, bot: Bot, event: GroupMessageEvent, message: str) -> None:
    await make_ops(bot).send_group_msg(event.group_id, message)
    await matcher.finish()


async def ensure_manager(bot: Bot, event: GroupMessageEvent, required_role: QGuardRole = QGuardRole.GROUP_ADMIN) -> str | None:
    async with get_session() as session:
        decision = await PermissionService(session).can_operate(
            make_ops(bot),
            group_id=event.group_id,
            operator_id=event.user_id,
            required_role=required_role,
        )
        if not decision.allowed:
            await AuditLogRepo(session).create(
                group_id=event.group_id,
                operator_id=event.user_id,
                action=AuditAction.PERMISSION_DENIED,
                result=AuditResult.SKIPPED,
                reason=decision.reason,
                metadata={
                    "required_role": int(required_role),
                    "operator_role": int(decision.operator_role),
                },
            )
            await session.commit()
    return None if decision.allowed else decision.reason
