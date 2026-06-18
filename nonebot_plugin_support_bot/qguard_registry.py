from __future__ import annotations

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, RegistryContext, register_plugin
from nonebot_plugin_support_bot.config import load_config
from nonebot_plugin_support_bot.services.support_service import SupportBotService


def _cmd(
    usage: str,
    summary: str,
    role: QGuardRole,
    *,
    reply_category: str = "chat_reply",
) -> CommandDescriptor:
    return CommandDescriptor(
        command=usage.split(maxsplit=1)[0],
        summary=summary,
        usage=usage,
        category="support",
        required_role=role,
        reply_category=reply_category,  # type: ignore[arg-type]
    )


async def _status_provider(context: RegistryContext) -> str:
    status = await SupportBotService(load_config()).status(context.group_id)
    parts = []
    for line in status.splitlines()[1:]:
        if "：" in line:
            parts.append(line.replace("：", " ", 1))
    return "，".join(parts[:5]) or "已加载"


async def _enabled_provider(context: RegistryContext) -> bool | None:
    if context.group_id is None:
        return None
    return await SupportBotService(load_config()).is_group_enabled(context.group_id)


async def _enable_setter(context: RegistryContext, enabled: bool) -> str:
    if context.group_id is None:
        return "这个命令只能在群里使用。"
    return await SupportBotService(load_config()).set_enabled(context.group_id, enabled, context.user_id)


def get_qguard_descriptor() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="qinex_answer",
        display_name="QInEX 智能问答",
        module_name="nonebot_plugin_support_bot",
        description="按本群知识库范围回答 QInEX 映射软件问题。",
        commands=(
            _cmd("/求助 问题描述", "让智能客服按知识库回答", QGuardRole.MEMBER),
            _cmd("/售后 问题描述", "售后问答入口", QGuardRole.MEMBER),
            _cmd("/不会用 功能名称", "按功能名发起使用求助", QGuardRole.MEMBER),
            _cmd("@机器人 问题", "自然语言提问", QGuardRole.MEMBER),
            _cmd("/客服 帮助", "查看智能问答帮助", QGuardRole.MEMBER, reply_category="command_reply"),
            _cmd("/客服 状态", "查看智能问答状态", QGuardRole.MEMBER, reply_category="command_reply"),
            _cmd("/客服 开启", "开启本群智能问答", QGuardRole.GROUP_ADMIN, reply_category="command_reply"),
            _cmd("/客服 关闭", "关闭本群智能问答", QGuardRole.GROUP_ADMIN, reply_category="command_reply"),
            _cmd("/客服 模式 命令触发", "切换为命令触发模式", QGuardRole.GROUP_ADMIN, reply_category="command_reply"),
            _cmd("/客服 模式 智能监听", "切换为智能监听模式", QGuardRole.GROUP_ADMIN, reply_category="command_reply"),
        ),
        default_enabled=True,
        status_provider=_status_provider,
        group_enabled_provider=_enabled_provider,
        group_enable_setter=_enable_setter,
    )


def register_with_qguard() -> None:
    register_plugin(get_qguard_descriptor())
