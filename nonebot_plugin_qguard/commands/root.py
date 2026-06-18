from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.qguard_registry import get_qguard_descriptor
from nonebot_plugin_qguard.registry import (
    RegistryContext,
    build_help_text,
    build_plugin_help_text,
    build_plugin_list_text,
    build_plugin_status_text,
    build_single_plugin_status_text,
    register_plugin,
)
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.services.auto_recall_service import (
    deserialize_auto_recall_categories,
    format_auto_recall_categories,
    parse_auto_recall_categories,
)
from nonebot_plugin_qguard.utils.formatter import format_group_status
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, make_ops, parse_qguard_args

root_matcher = on_message(priority=5, block=False)
register_plugin(get_qguard_descriptor())

HELP_TEXT = build_help_text(QGuardRole.SUPER_ADMIN, include_all=True)


@root_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] not in {"帮助", "状态", "开启", "关闭", "自动撤回", "插件"}:
        return
    service = GroupConfigService()
    if args[0] == "帮助":
        role = await _get_operator_role(bot, event)
        query = " ".join(args[1:])
        await finish_reply(root_matcher, bot, event, build_help_text(role, query=query))
    if args[0] == "状态":
        config = await service.status(event.group_id)
        await finish_reply(root_matcher, bot, event, format_group_status(config))
    if args[0] == "插件":
        await _handle_plugin_center(bot, event, args)
    denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN)
    if denied:
        await finish_reply(root_matcher, bot, event, denied)
    if args[0] == "开启":
        result = await service.set_enabled(event.group_id, event.user_id, True)
        await finish_reply(root_matcher, bot, event, result.message)
    if args[0] == "关闭":
        result = await service.set_enabled(event.group_id, event.user_id, False)
        await finish_reply(root_matcher, bot, event, result.message)
    if args[0] == "自动撤回":
        if len(args) < 2:
            config = await service.status(event.group_id)
            current = "关闭" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds} 秒"
            categories = format_auto_recall_categories(
                deserialize_auto_recall_categories(config.auto_delete_reply_categories)
            )
            await finish_reply(
                root_matcher,
                bot,
                event,
                f"当前自动撤回：{current}，分类：{categories}。\n"
                "用法：/管 自动撤回 90s，关闭用 /管 自动撤回 0，分类用 /管 自动撤回 分类 指令|聊天|全部|关闭",
            )
        if args[1] in {"分类", "类型"}:
            if len(args) < 3:
                await finish_reply(root_matcher, bot, event, "用法：/管 自动撤回 分类 指令|聊天|全部|关闭")
            try:
                categories = parse_auto_recall_categories(args[2])
            except ValueError as exc:
                await finish_reply(root_matcher, bot, event, str(exc))
            result = await service.set_auto_delete_reply_categories(event.group_id, event.user_id, categories)
            await finish_reply(root_matcher, bot, event, result.message)
        try:
            seconds = parse_duration(args[1])
        except ValueError as exc:
            await finish_reply(root_matcher, bot, event, str(exc))
        result = await service.set_auto_delete_reply_seconds(event.group_id, event.user_id, seconds)
        await finish_reply(root_matcher, bot, event, result.message)


async def _handle_plugin_center(bot: Bot, event: GroupMessageEvent, args: list[str]) -> None:
    role = await _get_operator_role(bot, event)
    if len(args) == 1:
        await finish_reply(root_matcher, bot, event, build_plugin_list_text(role))

    action = args[1]
    if action in {"帮助", "help"}:
        if len(args) < 3:
            await finish_reply(root_matcher, bot, event, "用法：/管 插件 帮助 插件ID")
        await finish_reply(root_matcher, bot, event, build_plugin_help_text(args[2], role))

    if action == "状态":
        if role < QGuardRole.TRUSTED:
            await finish_reply(root_matcher, bot, event, "权限不足。")
        context = RegistryContext(group_id=event.group_id, user_id=event.user_id, role=role)
        if len(args) >= 3:
            await finish_reply(root_matcher, bot, event, await build_single_plugin_status_text(args[2], context))
        await finish_reply(root_matcher, bot, event, await build_plugin_status_text(context))

    if action in {"开", "关", "权限"}:
        await finish_reply(root_matcher, bot, event, "插件中心开关和权限覆盖还在下一阶段，本阶段先支持帮助和状态。")

    await finish_reply(root_matcher, bot, event, "用法：/管 插件，/管 插件 状态，/管 插件 帮助 插件ID")


async def _get_operator_role(bot: Bot, event: GroupMessageEvent) -> QGuardRole:
    async with get_session() as session:
        return await PermissionService(session).get_role(make_ops(bot), event.group_id, event.user_id)
