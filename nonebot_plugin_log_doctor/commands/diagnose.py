from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_log_doctor.config import load_config
from nonebot_plugin_log_doctor.services.diagnose_service import LogDoctorService
from nonebot_plugin_log_doctor.services.formatter import format_diagnosis, format_recent_records, format_rules
from nonebot_plugin_log_doctor.services.rule_engine import RuleEngine

from ._common import finish_reply, get_event_group_id, get_reply_text, parse_log_doctor_command

diagnose_matcher = on_message(priority=5, block=False)


@diagnose_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    parsed = parse_log_doctor_command(event.get_plaintext())
    if parsed is None:
        return
    _command, args = parsed
    service = LogDoctorService()
    group_id = get_event_group_id(event)

    if args in {"最近", "历史"}:
        records = await service.latest_records(group_id=group_id, limit=5)
        await finish_reply(diagnose_matcher, bot, event, format_recent_records(records))

    if args in {"规则列表", "已知错误"}:
        await finish_reply(diagnose_matcher, bot, event, format_rules(RuleEngine().list_rules()))

    source_type = "command"
    text = args
    if not text:
        text = get_reply_text(event)
        source_type = "reply" if text else "command"

    if not text:
        await finish_reply(diagnose_matcher, bot, event, "用法：/诊断 <日志文本>，或回复一条日志消息发送 /诊断。")

    response = await service.diagnose_text(
        text,
        group_id=group_id,
        user_id=event.user_id,
        source_type=source_type,
    )
    await finish_reply(diagnose_matcher, bot, event, format_diagnosis(response, load_config()))
