from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_qfun.config import load_config
from nonebot_plugin_qfun.services.wordcloud_service import QFunService

from ._common import check_qguard_command_permission, finish_reply, get_event_group_id, parse_qfun_command

qfun_matcher = on_message(priority=6, block=False)

HELP_TEXT = """QFun 命令
/娱乐 帮助
/娱乐 状态
/娱乐 开启
/娱乐 关闭
/娱乐 词云
/娱乐 词云 今日
/娱乐 词云 昨日
/娱乐 词云 7天
/娱乐 词云定时 状态
/娱乐 词云定时 开 21:30
/娱乐 词云定时 开 21:30 7天
/娱乐 词云定时 关
"""


@qfun_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    parsed = parse_qfun_command(event.get_plaintext())
    if parsed is None:
        return
    command, actions, args_text = parsed
    action = actions[0] if actions else "帮助"
    group_id = get_event_group_id(event)
    service = QFunService(load_config())
    selector = _permission_selector(command, action)
    fallback_role = _fallback_role(action)

    permission = await check_qguard_command_permission(
        bot,
        event,
        selector=selector,
        fallback_role=fallback_role,
        enforce_plugin_enabled=action != "开启",
    )
    if permission.denied_reason:
        await finish_reply(qfun_matcher, bot, event, permission.denied_reason)

    if action in {"帮助", "help"}:
        await finish_reply(qfun_matcher, bot, event, HELP_TEXT)
    if group_id is None:
        await finish_reply(qfun_matcher, bot, event, "QFun 命令只能在群里使用。")

    if action == "状态":
        await finish_reply(qfun_matcher, bot, event, await service.status(group_id))
    if action == "开启":
        await finish_reply(qfun_matcher, bot, event, await service.set_enabled(group_id, True, event.user_id))
    if action == "关闭":
        await finish_reply(qfun_matcher, bot, event, await service.set_enabled(group_id, False, event.user_id))

    if not await service.is_group_enabled(group_id):
        await finish_reply(qfun_matcher, bot, event, "QFun 已在本群关闭。")

    if action == "词云":
        period = args_text.strip() or "今日"
        try:
            text = await service.render_wordcloud(group_id, period)
        except ValueError as exc:
            await finish_reply(qfun_matcher, bot, event, str(exc))
        await finish_reply(qfun_matcher, bot, event, text)

    if action == "词云定时":
        await _handle_wordcloud_schedule(service, group_id, event.user_id, args_text, bot, event)

    await finish_reply(qfun_matcher, bot, event, HELP_TEXT)


async def _handle_wordcloud_schedule(
    service: QFunService,
    group_id: int,
    user_id: int,
    args_text: str,
    bot: Bot,
    event: MessageEvent,
) -> None:
    args = args_text.split()
    if not args or args[0] in {"状态", "status"}:
        await finish_reply(qfun_matcher, bot, event, await service.status(group_id))
    if args[0] in {"关", "关闭", "off"}:
        await finish_reply(
            qfun_matcher,
            bot,
            event,
            await service.set_wordcloud_schedule(group_id, enabled=False, operator_id=user_id),
        )
    if args[0] in {"开", "开启", "on"}:
        if len(args) < 2:
            await finish_reply(qfun_matcher, bot, event, "用法：/娱乐 词云定时 开 21:30，可加范围：7天")
        try:
            result = await service.set_wordcloud_schedule(
                group_id,
                enabled=True,
                schedule_time=args[1],
                period_text=args[2] if len(args) >= 3 else None,
                operator_id=user_id,
            )
        except ValueError as exc:
            await finish_reply(qfun_matcher, bot, event, str(exc))
        await finish_reply(qfun_matcher, bot, event, result)
    await finish_reply(qfun_matcher, bot, event, "用法：/娱乐 词云定时 开 21:30，或 /娱乐 词云定时 关")


def _permission_selector(command: str, action: str) -> str:
    if action in {"帮助", "help"}:
        return command
    return f"{command} {action}"


def _fallback_role(action: str) -> int:
    if action in {"词云", "帮助", "help", "状态"}:
        return 0
    return 3
