from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.card_lock_service import CardLockService
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.utils.message_parser import parse_target

from ._common import ensure_manager, make_ops, parse_qguard_args

card_lock_matcher = on_message(priority=5, block=False)


@card_lock_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"名片锁", "名片解锁", "名片锁列表", "名片扫描", "名片修复", "名片锁全群"}:
        return
    ops = make_ops(bot)
    service = CardLockService()

    if args[0] == "名片锁全群":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_OWNER)
        if denied:
            await card_lock_matcher.finish(denied)
        if len(args) < 2 or args[1] not in {"开", "关"}:
            await card_lock_matcher.finish("用法：/管 名片锁全群 开|关")
        result = await GroupConfigService().set_card_lock_enabled(event.group_id, event.user_id, args[1] == "开")
        await card_lock_matcher.finish(result.message)

    if args[0] == "名片锁列表":
        locks = await service.list_locks(event.group_id)
        if not locks:
            await card_lock_matcher.finish("当前没有启用中的名片锁。")
        lines = ["名片锁列表："]
        for item in locks:
            lines.append(f"{item.user_id}: {item.locked_card}")
        await card_lock_matcher.finish("\n".join(lines))

    if args[0] in {"名片扫描", "名片修复"}:
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
        if denied:
            await card_lock_matcher.finish(denied)
        result = await service.scan_group(ops, event.group_id, event.user_id, fix=args[0] == "名片修复")
        await card_lock_matcher.finish(
            f"扫描完成：检查 {result.scanned} 人，异常 {result.mismatched} 人，修复 {result.fixed} 人，失败 {result.failed} 人。"
        )

    parsed = parse_target(event, args)
    if parsed is None:
        await card_lock_matcher.finish("请指定目标用户，支持 @用户 或 QQ 号。")

    if args[0] == "名片锁":
        if not parsed.rest:
            await card_lock_matcher.finish("用法：/管 名片锁 @用户 固定名片")
        result = await service.lock_card(ops, event.group_id, event.user_id, parsed.user_id, parsed.rest)
        await card_lock_matcher.finish(result.message)
    if args[0] == "名片解锁":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_OWNER)
        if denied:
            await card_lock_matcher.finish(denied)
        result = await service.unlock_card(event.group_id, event.user_id, parsed.user_id)
        await card_lock_matcher.finish(result.message)
