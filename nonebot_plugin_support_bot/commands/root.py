from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.rule import Rule

from nonebot_plugin_support_bot.config import load_config
from nonebot_plugin_support_bot.services.support_service import SupportBotService
from nonebot_plugin_support_bot.services.ticket_service import TicketService
from nonebot_plugin_support_bot.utils.formatter import format_ticket, format_ticket_list

from ._common import (
    finish_reply,
    get_event_group_id,
    get_reply_text,
    is_admin_event,
    is_smart_candidate,
    parse_support_command,
)

HELP_TEXT = """SupportBot 命令
/客服 帮助
/客服 状态
/客服 开启
/客服 关闭
/客服 模式 命令触发
/客服 模式 智能监听
/求助 问题描述
/报错 日志或描述
/不会用 功能名称
/人工
/工单 创建 问题
/工单 我的
/工单 列表
/工单 查看 T202606170001
/工单 接单 T202606170001
/工单 备注 T202606170001 内容
/工单 关闭 T202606170001
/工单 重开 T202606170001
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
    ticket_service = TicketService(config)
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

    if command == "/报错":
        text = args_text or get_reply_text(event)
        if not text:
            await finish_reply(support_command, bot, event, "用法：/报错 <日志或报错描述>，也可以回复一条日志消息发送 /报错。")
        reply = await service.handle_user_issue(text, group_id=group_id, user_id=event.user_id, force_log=True)
        await finish_reply(support_command, bot, event, reply.text)

    if command == "/人工":
        text = args_text or "用户请求人工处理"
        reply = await service.handle_user_issue(text, group_id=group_id, user_id=event.user_id, force_ticket=True)
        await finish_reply(support_command, bot, event, reply.text)

    if command == "/工单":
        action = actions[0] if actions else "帮助"
        await _handle_ticket_command(
            bot=bot,
            event=event,
            action=action,
            args_text=args_text,
            group_id=group_id,
            is_admin=is_admin,
            service=service,
            ticket_service=ticket_service,
        )


@support_smart.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    group_id = get_event_group_id(event)
    service = SupportBotService()
    if not await service.should_smart_listen(group_id):
        return
    reply = await service.handle_user_issue(event.get_plaintext(), group_id=group_id, user_id=event.user_id)
    await finish_reply(support_smart, bot, event, reply.text)


async def _handle_ticket_command(
    *,
    bot: Bot,
    event: MessageEvent,
    action: str,
    args_text: str,
    group_id: int | None,
    is_admin: bool,
    service: SupportBotService,
    ticket_service: TicketService,
) -> None:
    if action in {"帮助", "help"}:
        await finish_reply(support_command, bot, event, HELP_TEXT)
    if group_id is None:
        await finish_reply(support_command, bot, event, "工单命令只能在群里使用。")
    if action == "创建":
        if not args_text:
            await finish_reply(support_command, bot, event, "用法：/工单 创建 <问题>")
        reply = await service.handle_user_issue(args_text, group_id=group_id, user_id=event.user_id, force_ticket=True)
        await finish_reply(support_command, bot, event, reply.text)
    if action == "我的":
        tickets = await ticket_service.list_user_tickets(group_id, event.user_id)
        await finish_reply(support_command, bot, event, format_ticket_list(tickets))
    if action == "列表":
        if not is_admin:
            await finish_reply(support_command, bot, event, "只有管理员可以查看群内工单列表。")
        tickets = await ticket_service.list_group_tickets(group_id)
        await finish_reply(support_command, bot, event, format_ticket_list(tickets))
    if action == "查看":
        ticket_no = args_text.strip().upper()
        if not ticket_no:
            await finish_reply(support_command, bot, event, "用法：/工单 查看 T202606170001")
        ticket, messages = await ticket_service.get_ticket(ticket_no)
        if ticket is None:
            await finish_reply(support_command, bot, event, "没有找到这个工单。")
        if not is_admin and ticket.user_id != event.user_id:
            await finish_reply(support_command, bot, event, "只能查看自己的工单。")
        await finish_reply(support_command, bot, event, format_ticket(ticket, messages))
    if action == "接单":
        if not is_admin:
            await finish_reply(support_command, bot, event, "只有管理员可以接单。")
        ticket = await ticket_service.assign_ticket(args_text.strip().upper(), event.user_id)
        await finish_reply(support_command, bot, event, "没有找到这个工单。" if ticket is None else f"已接单：{ticket.ticket_no}")
    if action == "备注":
        ticket_no, content = _split_ticket_no_content(args_text)
        if not is_admin:
            await finish_reply(support_command, bot, event, "只有管理员可以备注工单。")
        if not ticket_no or not content:
            await finish_reply(support_command, bot, event, "用法：/工单 备注 T202606170001 内容")
        ticket = await ticket_service.add_note(ticket_no, sender_id=event.user_id, sender_role="admin", content=content)
        await finish_reply(support_command, bot, event, "没有找到这个工单。" if ticket is None else f"已备注：{ticket.ticket_no}")
    if action in {"关闭", "重开"}:
        if not is_admin:
            await finish_reply(support_command, bot, event, "只有管理员可以修改工单状态。")
        ticket_no = args_text.strip().upper()
        if not ticket_no:
            await finish_reply(support_command, bot, event, f"用法：/工单 {action} T202606170001")
        status = "closed" if action == "关闭" else "open"
        ticket = await ticket_service.set_status(ticket_no, status, operator_id=event.user_id)
        await finish_reply(support_command, bot, event, "没有找到这个工单。" if ticket is None else f"工单已{action}：{ticket.ticket_no}")
    await finish_reply(support_command, bot, event, HELP_TEXT)


def _parse_mode(text: str) -> str:
    stripped = text.strip()
    if stripped in {"命令触发", "命令", "command"}:
        return "command"
    if stripped in {"智能监听", "智能", "smart"}:
        return "smart"
    return ""


def _split_ticket_no_content(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "", ""
    return parts[0].upper(), parts[1]
