from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.join_review_service import JoinReviewService
from nonebot_plugin_qguard.services.join_welcome_service import JoinWelcomeService

from ._common import ensure_manager, finish_reply, parse_qguard_args

join_review_matcher = on_message(priority=5, block=False)


@join_review_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"入群审核", "入群暗号", "入群拒绝理由", "入群欢迎"}:
        return

    denied = await ensure_manager(
        bot,
        event,
        QGuardRole.GROUP_ADMIN,
        command_selector=_command_selector(args),
    )
    if denied:
        await finish_reply(join_review_matcher, bot, event, denied)

    service = JoinReviewService()
    welcome_service = JoinWelcomeService()

    if args[0] == "入群审核":
        if len(args) < 2 or args[1] not in {"开", "关"}:
            await finish_reply(join_review_matcher, bot, event, "用法：/管 入群审核 开|关")
        result = await service.set_enabled(event.group_id, event.user_id, args[1] == "开")
        await finish_reply(join_review_matcher, bot, event, result.message)

    if args[0] == "入群暗号":
        if len(args) < 3 or args[1] != "设置":
            await finish_reply(join_review_matcher, bot, event, "用法：/管 入群暗号 设置 xxx")
        result = await service.set_answer(event.group_id, event.user_id, " ".join(args[2:]))
        await finish_reply(join_review_matcher, bot, event, result.message)

    if args[0] == "入群拒绝理由":
        if len(args) < 3 or args[1] != "设置":
            await finish_reply(join_review_matcher, bot, event, "用法：/管 入群拒绝理由 设置 xxx")
        result = await service.set_reject_reason(event.group_id, event.user_id, " ".join(args[2:]))
        await finish_reply(join_review_matcher, bot, event, result.message)

    if args[0] == "入群欢迎":
        if len(args) < 2:
            await finish_reply(
                join_review_matcher,
                bot,
                event,
                "用法：/管 入群欢迎 开|关|状态，/管 入群欢迎 模板 默认，/管 入群欢迎 模板 文本",
            )
        if args[1] in {"开", "关"}:
            result = await welcome_service.set_enabled(event.group_id, event.user_id, args[1] == "开")
            await finish_reply(join_review_matcher, bot, event, result.message)
        if args[1] == "状态":
            await finish_reply(join_review_matcher, bot, event, await welcome_service.status(event.group_id))
        if args[1] == "模板":
            if len(args) < 3:
                await finish_reply(join_review_matcher, bot, event, "用法：/管 入群欢迎 模板 默认，或 /管 入群欢迎 模板 文本")
            result = await welcome_service.set_template(event.group_id, event.user_id, " ".join(args[2:]))
            await finish_reply(join_review_matcher, bot, event, result.message)
        await finish_reply(
            join_review_matcher,
            bot,
            event,
            "用法：/管 入群欢迎 开|关|状态，/管 入群欢迎 模板 默认，/管 入群欢迎 模板 文本",
        )


def _command_selector(args: list[str]) -> str:
    if args[0] == "入群欢迎":
        if len(args) >= 2 and args[1] == "模板":
            return "/管 入群欢迎 模板 文本"
        if len(args) >= 2 and args[1] in {"关", "状态"}:
            return f"/管 入群欢迎 {args[1]}"
        return "/管 入群欢迎 开"
    if args[0] == "入群暗号":
        return "/管 入群暗号 设置 xxx"
    if args[0] == "入群拒绝理由":
        return "/管 入群拒绝理由 设置 xxx"
    return "/管 入群审核 关" if len(args) >= 2 and args[1] == "关" else "/管 入群审核 开"
