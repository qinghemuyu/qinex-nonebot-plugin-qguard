from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.score_service import ScoreService
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, finish_reply, parse_qguard_args

score_matcher = on_message(priority=5, block=False)


@score_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "积分":
        return

    service = ScoreService()
    if len(args) >= 2 and args[1] == "清零":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
        if denied:
            await finish_reply(score_matcher, bot, event, denied)
        parsed = parse_target(event, args, target_index=2)
        if parsed is None:
            await finish_reply(score_matcher, bot, event, "用法：/管 积分 清零 @用户")
        result = await service.reset_score(event.group_id, event.user_id, parsed.user_id)
        await finish_reply(score_matcher, bot, event, result.message)

    parsed = parse_target(event, args, target_index=1)
    if parsed is None:
        await finish_reply(score_matcher, bot, event, "用法：/管 积分 @用户")
    result = await service.get_score(event.group_id, parsed.user_id)
    await finish_reply(score_matcher, bot, event, f"{parsed.user_id} 当前违规积分：{result.current_score}")
