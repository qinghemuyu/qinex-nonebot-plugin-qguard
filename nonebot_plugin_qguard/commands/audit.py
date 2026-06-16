from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.utils.formatter import format_audit_logs

from ._common import finish_reply, parse_qguard_args

audit_matcher = on_message(priority=5, block=False)


@audit_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if len(args) < 2 or args[0] != "日志" or args[1] != "最近":
        return
    async with get_session() as session:
        logs = await AuditLogRepo(session).latest(event.group_id, limit=10)
    await finish_reply(audit_matcher, bot, event, format_audit_logs(logs))
