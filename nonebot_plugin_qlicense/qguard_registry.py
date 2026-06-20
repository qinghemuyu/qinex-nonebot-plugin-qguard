from __future__ import annotations

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, register_plugin


def _cmd(usage: str, summary: str, role: QGuardRole) -> CommandDescriptor:
    return CommandDescriptor(
        command=usage.split(maxsplit=1)[0],
        summary=summary,
        usage=usage,
        category="system",
        required_role=role,
        reply_category="command_reply",
    )


def get_qguard_descriptor() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="qlicense",
        display_name="QInEX 授权登记",
        module_name="nonebot_plugin_qlicense",
        description="S3 板子自助登记、QQ 授权配额和历史授权同步。",
        commands=(
            _cmd("/激活 S3 MAC", "登记自己的 S3 板子 MAC", QGuardRole.MEMBER),
            _cmd("/激活 状态", "查看自己的 S3 授权额度", QGuardRole.MEMBER),
            _cmd("/授权 查询 QQ", "查询 QQ 授权状态", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 配额 QQ 数量", "设置 QQ 的 S3 配额", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 默认配额 数量", "设置全局默认 S3 配额", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 解绑 MAC", "解绑并停用设备", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 禁用 MAC", "禁用设备", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 恢复 MAC", "恢复设备", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 预检 MAC", "预检设备能否在线激活", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 同步预览", "预览 description 历史 QQ 同步", QGuardRole.SUPER_ADMIN),
            _cmd("/授权 同步执行", "执行 description 历史 QQ 同步", QGuardRole.SUPER_ADMIN),
        ),
        default_enabled=True,
    )


def register_with_qguard() -> None:
    register_plugin(get_qguard_descriptor())
