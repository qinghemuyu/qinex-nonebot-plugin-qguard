from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.rule import Rule

from nonebot_plugin_support_bot.config import load_config
from nonebot_plugin_support_bot.services.support_service import SupportBotService

from ._common import (
    finish_reply,
    get_event_group_id,
    get_reply_text,
    is_admin_event,
    is_smart_candidate,
    parse_support_command,
)

HELP_TEXT = """SupportBot 知识问答命令
/客服 帮助
/客服 状态
/客服 开启
/客服 关闭
/客服 模式 命令触发
/客服 模式 智能监听
/求助 问题描述
/售后 问题描述
/不会用 功能名称

知识库范围由 /知识 范围 管理。
日志诊断请使用 /诊断 或 /报错。
"""


def _is_support_command(event: MessageEvent) -> bool:
    return parse_support_command(event.get_plaintext()) is not None


def _is_smart_candidate(event: MessageEvent) -> bool:
    return is_smart_candidate(event.get_plaintext())


support_command = on_message(rule=Rule(_is_support_command), priority=4, block=True)
support_smart = on_message(rule=Rule(_is_smart_candidate), priority=20, block=False)


@support_command.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    parsed = parse_support_command(event.get_plaintext())
    if parsed is None:
        return
    command, actions, args_text = parsed
    config = load_config()
    service = SupportBotService(config)
    group_id = get_event_group_id(event)
    is_admin = is_admin_event(event, config.support_bot_admins)

    if command == "/客服":
        action = actions[0] if actions else "帮助"
        if action in {"帮助", "help"}:
            await finish_reply(support_command, bot, event, HELP_TEXT)
        if action == "状态":
            await finish_reply(support_command, bot, event, await service.status(group_id))
        if action in {"开启", "关闭"}:
            if group_id is None:
                await finish_reply(support_command, bot, event, "这个命令只能在群里使用。")
            if not is_admin:
                await finish_reply(support_command, bot, event, "只有管理员可以修改 SupportBot 开关。")
            await finish_reply(
                support_command,
                bot,
                event,
                await service.set_enabled(group_id, action == "开启", event.user_id),
            )
        if action == "模式":
            if group_id is None:
                await finish_reply(support_command, bot, event, "这个命令只能在群里使用。")
            if not is_admin:
                await finish_reply(support_command, bot, event, "只有管理员可以修改 SupportBot 模式。")
            mode = _parse_mode(args_text)
            if mode == "":
                await finish_reply(support_command, bot, event, "用法：/客服 模式 命令触发 或 /客服 模式 智能监听")
            await finish_reply(support_command, bot, event, await service.set_mode(group_id, mode, event.user_id))
        await finish_reply(support_command, bot, event, HELP_TEXT)

    if command in {"/求助", "/售后", "/不会用"}:
        text = args_text or get_reply_text(event)
        if command == "/不会用" and text:
            text = f"不会用 {text}"
        if not text:
            await finish_reply(support_command, bot, event, "用法：/求助 <问题描述>")
        reply = await service.handle_user_issue(text, group_id=group_id, user_id=event.user_id)
        await finish_reply(support_command, bot, event, reply.text)


@support_smart.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    group_id = get_event_group_id(event)
    service = SupportBotService()
    if not await service.should_smart_listen(group_id):
        return
    reply = await service.handle_user_issue(event.get_plaintext(), group_id=group_id, user_id=event.user_id)
    await finish_reply(support_smart, bot, event, reply.text)


def _parse_mode(text: str) -> str:
    stripped = text.strip()
    if stripped in {"命令触发", "命令", "command"}:
        return "command"
    if stripped in {"智能监听", "智能", "smart"}:
        return "smart"
    return ""
