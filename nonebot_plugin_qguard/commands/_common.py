from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.config import Config, load_config
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.utils.message_parser import split_command


def get_plugin_config() -> Config:
    return load_config()


def parse_qguard_args(event: GroupMessageEvent) -> list[str]:
    config = get_plugin_config()
    return split_command(config.qguard_command_prefix, event.get_plaintext())


def make_ops(bot: Bot) -> OneBotV11GroupOps:
    return OneBotV11GroupOps(bot)


async def ensure_manager(bot: Bot, event: GroupMessageEvent, required_role: QGuardRole = QGuardRole.GROUP_ADMIN) -> str | None:
    async with get_session() as session:
        decision = await PermissionService(session).can_operate(
            make_ops(bot),
            group_id=event.group_id,
            operator_id=event.user_id,
            required_role=required_role,
        )
    return None if decision.allowed else decision.reason
