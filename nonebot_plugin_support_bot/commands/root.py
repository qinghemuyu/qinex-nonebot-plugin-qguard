from types import SimpleNamespace
from typing import Any

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.rule import Rule, to_me

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

HELP_TEXT = """QInEX 智能问答命令
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
可用 skills 用 /知识 技能 查看。
"""


def _is_support_command(event: MessageEvent) -> bool:
    return parse_support_command(event.get_plaintext()) is not None


def _is_smart_candidate(event: MessageEvent) -> bool:
    return is_smart_candidate(event.get_plaintext())


def _is_mention_question(event: MessageEvent) -> bool:
    text = event.get_plaintext().strip()
    return bool(text) and not text.startswith("/") and parse_support_command(text) is None


async def _is_support_continuation(event: MessageEvent) -> bool:
    text = event.get_plaintext().strip()
    if not text or text.startswith("/") or parse_support_command(text) is not None:
        return False
    group_id = get_event_group_id(event)
    if group_id is None:
        return False
    config = load_config()
    service = SupportBotService(config)
    return await service.should_handle_continuation(text, group_id=group_id, user_id=int(event.user_id))


support_command = on_message(rule=Rule(_is_support_command), priority=4, block=True)
support_mention = on_message(rule=to_me() & Rule(_is_mention_question), priority=18, block=True)
support_continuation = on_message(rule=Rule(_is_support_continuation), priority=19, block=True)
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
                await finish_reply(support_command, bot, event, "只有管理员可以修改 QInEX 智能问答开关。")
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
                await finish_reply(support_command, bot, event, "只有管理员可以修改 QInEX 智能问答模式。")
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
        await _finish_support_response(support_command, bot, event, service, config, text, reply)


@support_mention.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    text = event.get_plaintext().strip()
    config = load_config()
    service = SupportBotService(config)
    group_id = get_event_group_id(event)
    reply = await service.handle_user_issue(text, group_id=group_id, user_id=event.user_id)
    await _finish_support_response(support_mention, bot, event, service, config, text, reply)


@support_continuation.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    text = event.get_plaintext().strip()
    config = load_config()
    service = SupportBotService(config)
    group_id = get_event_group_id(event)
    reply = await service.handle_user_issue(text, group_id=group_id, user_id=event.user_id)
    await _finish_support_response(support_continuation, bot, event, service, config, text, reply)


@support_smart.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    group_id = get_event_group_id(event)
    config = load_config()
    service = SupportBotService(config)
    if not await service.should_smart_listen(group_id):
        return
    reply = await service.handle_user_issue(event.get_plaintext(), group_id=group_id, user_id=event.user_id)
    await _finish_support_response(support_smart, bot, event, service, config, event.get_plaintext(), reply)


def _parse_mode(text: str) -> str:
    stripped = text.strip()
    if stripped in {"命令触发", "命令", "command"}:
        return "command"
    if stripped in {"智能监听", "智能", "smart"}:
        return "smart"
    return ""


async def _notify_owner_if_needed(
    bot: Bot,
    event: MessageEvent,
    service: SupportBotService,
    config,
    question: str,
    reply,
) -> None:
    record_no = getattr(reply, "no_answer_id", "")
    if getattr(reply, "state", "") != "no_answer" or not record_no:
        return
    group_id = get_event_group_id(event)
    message = (
        "QInEX 智能问答未命中\n"
        f"记录：{record_no}\n"
        f"群：{group_id or '私聊'}\n"
        f"用户：{event.user_id}\n"
        f"问题：{question.strip()[:800]}\n"
        f"机器人回复：{str(getattr(reply, 'text', '')).strip()[:800]}"
    )
    notified = False
    for owner_id in config.support_bot_admins:
        try:
            await bot.send_private_msg(user_id=int(owner_id), message=message)
            notified = True
        except Exception:
            continue
    if notified:
        await service.mark_no_answer_notified(record_no)


async def _finish_support_response(
    matcher: Any,
    bot: Bot,
    event: MessageEvent,
    service: SupportBotService,
    config,
    question: str,
    reply,
) -> None:
    score_result = await _apply_harassment_score(bot, event, config, reply)
    if score_result is not None:
        line = f"群管积分：+{score_result.delta}，当前 {score_result.current_score}"
        if score_result.penalty_action:
            line += f"，已触发 {score_result.penalty_action}"
        reply.text = f"{reply.text}\n{line}"
    await _notify_owner_if_needed(bot, event, service, config, question, reply)
    await finish_reply(matcher, bot, event, reply.text)


async def _apply_harassment_score(bot: Bot, event: MessageEvent, config, reply):
    delta = int(getattr(reply, "harassment_score_delta", 0) or 0)
    group_id = get_event_group_id(event)
    if delta <= 0 or group_id is None:
        return None
    if is_admin_event(event, config.support_bot_admins):
        return None
    try:
        from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
        from nonebot_plugin_qguard.enums import RuleAction
        from nonebot_plugin_qguard.models.base import get_session as get_qguard_session
        from nonebot_plugin_qguard.services.permission_service import PermissionService
        from nonebot_plugin_qguard.services.rule_engine import ModerationDecision
        from nonebot_plugin_qguard.services.score_service import ScoreService
    except Exception:
        return None
    ops = OneBotV11GroupOps(bot)
    async with get_qguard_session() as session:
        protected = await PermissionService(session).is_protected_from_auto_action(ops, int(group_id), int(event.user_id))
        if protected:
            return None

    fake_event = SimpleNamespace(
        group_id=int(group_id),
        user_id=int(event.user_id),
        message_id=int(getattr(event, "message_id", 0) or 0),
    )
    decision = ModerationDecision(
        hit=True,
        action=RuleAction.WARN.value,
        reason=str(getattr(reply, "harassment_reason", "") or "骚扰智能客服"),
        score_delta=delta,
    )
    return await ScoreService().apply_decision_score(ops, _bot_id(bot), fake_event, decision)


def _bot_id(bot: Bot) -> int:
    try:
        return int(bot.self_id)
    except (TypeError, ValueError):
        return 0
