from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.ad_keyword_service import AdKeywordService
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService

from ._common import ensure_manager, finish_reply, parse_qguard_args

moderation_matcher = on_message(priority=5, block=False)


@moderation_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"广告检测", "刷屏检测", "广告词"}:
        return

    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(moderation_matcher, bot, event, denied)

    if args[0] == "广告词":
        await _handle_ad_keyword(bot, event, args)
        return

    if len(args) < 2 or args[1] not in {"开", "关"}:
        await finish_reply(moderation_matcher, bot, event, f"用法：/管 {args[0]} 开|关")

    service = GroupConfigService()
    enabled = args[1] == "开"
    if args[0] == "广告检测":
        result = await service.set_anti_ad_enabled(event.group_id, event.user_id, enabled)
    else:
        result = await service.set_anti_spam_enabled(event.group_id, event.user_id, enabled)
    await finish_reply(moderation_matcher, bot, event, result.message)


async def _handle_ad_keyword(bot: Bot, event: GroupMessageEvent, args: list[str]) -> None:
    service = AdKeywordService()
    if len(args) < 2:
        await finish_reply(
            moderation_matcher,
            bot,
            event,
            "用法：/管 广告词 添加 xxx，/管 广告词 删除 ID，/管 广告词 列表",
        )

    if args[1] == "添加":
        if len(args) < 3:
            await finish_reply(moderation_matcher, bot, event, "用法：/管 广告词 添加 xxx")
        result = await service.add(event.group_id, event.user_id, " ".join(args[2:]))
        await finish_reply(moderation_matcher, bot, event, result.message)

    if args[1] == "删除":
        if len(args) < 3 or not args[2].isdigit():
            await finish_reply(moderation_matcher, bot, event, "用法：/管 广告词 删除 ID")
        result = await service.remove(event.group_id, event.user_id, int(args[2]))
        await finish_reply(moderation_matcher, bot, event, result.message)

    if args[1] == "列表":
        items = await service.list(event.group_id)
        if not items:
            await finish_reply(moderation_matcher, bot, event, "当前没有广告词。")
        lines = ["广告词列表："]
        for item in items:
            status = "启用" if item.enabled else "停用"
            lines.append(f"#{item.id} [{status}] {item.keyword}")
        await finish_reply(moderation_matcher, bot, event, "\n".join(lines))

    await finish_reply(
        moderation_matcher,
        bot,
        event,
        "用法：/管 广告词 添加 xxx，/管 广告词 删除 ID，/管 广告词 列表",
    )
