from __future__ import annotations

from nonebot_plugin_qfun.config import load_config
from nonebot_plugin_qfun.services.wordcloud_service import QFunService
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, RegistryContext, register_plugin


def _cmd(
    usage: str,
    summary: str,
    role: QGuardRole,
    *,
    reply_category: str = "command_reply",
) -> CommandDescriptor:
    return CommandDescriptor(
        command=usage.split(maxsplit=1)[0],
        summary=summary,
        usage=usage,
        category="other",
        required_role=role,
        reply_category=reply_category,  # type: ignore[arg-type]
    )


async def _status_provider(context: RegistryContext) -> str:
    return await QFunService(load_config()).status(context.group_id)


async def _enabled_provider(context: RegistryContext) -> bool | None:
    if context.group_id is None:
        return None
    return await QFunService(load_config()).is_group_enabled(context.group_id)


async def _enable_setter(context: RegistryContext, enabled: bool) -> str:
    if context.group_id is None:
        return "这个命令只能在群里使用。"
    return await QFunService(load_config()).set_enabled(context.group_id, enabled, context.user_id)


def get_qguard_descriptor() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="qfun",
        display_name="QFun 群娱乐",
        module_name="nonebot_plugin_qfun",
        description="群娱乐和轻量统计插件，支持聊天词云与每日定时推送。",
        commands=(
            _cmd("/娱乐 帮助", "查看 QFun 帮助", QGuardRole.MEMBER),
            _cmd("/娱乐 状态", "查看 QFun 状态", QGuardRole.MEMBER),
            _cmd("/娱乐 词云", "生成本群今日词云", QGuardRole.MEMBER),
            _cmd("/娱乐 词云 7天", "生成指定范围词云", QGuardRole.MEMBER),
            _cmd("/娱乐 词云定时 状态", "查看每日词云定时状态", QGuardRole.MEMBER),
            _cmd("/娱乐 词云定时 开 21:30", "开启每日词云定时发送", QGuardRole.GROUP_ADMIN),
            _cmd("/娱乐 词云定时 关", "关闭每日词云定时发送", QGuardRole.GROUP_ADMIN),
            _cmd("/娱乐 开启", "开启本群 QFun", QGuardRole.GROUP_ADMIN),
            _cmd("/娱乐 关闭", "关闭本群 QFun", QGuardRole.GROUP_ADMIN),
        ),
        default_enabled=True,
        status_provider=_status_provider,
        group_enabled_provider=_enabled_provider,
        group_enable_setter=_enable_setter,
    )


def register_with_qguard() -> None:
    register_plugin(get_qguard_descriptor())
