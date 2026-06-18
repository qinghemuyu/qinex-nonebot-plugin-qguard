from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.services.member_role_service import ROLE_LABELS

CommandScope = Literal["group", "private", "both"]
ReplyCategory = Literal["command_reply", "chat_reply", "moderation_notice"]
CommandCategory = Literal["qguard", "ai", "knowledge", "support", "system", "other"]


@dataclass(frozen=True)
class RegistryContext:
    group_id: int | None = None
    user_id: int | None = None
    role: QGuardRole = QGuardRole.MEMBER


StatusProvider = Callable[[RegistryContext], Awaitable[str] | str]
HealthCheck = Callable[[RegistryContext], Awaitable[bool] | bool]
GroupEnabledProvider = Callable[[RegistryContext], Awaitable[bool | None] | bool | None]
GroupEnableSetter = Callable[[RegistryContext, bool], Awaitable[str] | str]


@dataclass(frozen=True)
class CommandDescriptor:
    command: str
    summary: str
    usage: str
    category: CommandCategory
    required_role: QGuardRole = QGuardRole.MEMBER
    aliases: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    scope: CommandScope = "group"
    reply_category: ReplyCategory = "command_reply"
    show_in_help: bool = True
    enabled_by_default: bool = True
    danger_level: int = 0


@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    display_name: str
    module_name: str
    description: str
    commands: tuple[CommandDescriptor, ...] = field(default_factory=tuple)
    version: str = ""
    default_enabled: bool = True
    show_in_help: bool = True
    status_provider: StatusProvider | None = None
    health_check: HealthCheck | None = None
    group_enabled_provider: GroupEnabledProvider | None = None
    group_enable_setter: GroupEnableSetter | None = None


_REGISTRY: dict[str, PluginDescriptor] = {}
_DISCOVERED: set[str] = set()
_KNOWN_PLUGIN_MODULES = (
    "nonebot_plugin_ai_core",
    "nonebot_plugin_group_wiki",
    "nonebot_plugin_support_bot",
)
CATEGORY_LABELS: dict[str, str] = {
    "qguard": "群管",
    "ai": "AI Core",
    "knowledge": "知识库",
    "support": "QInEX 智能问答",
    "system": "系统",
    "other": "其他",
}


def register_plugin(descriptor: PluginDescriptor) -> None:
    if descriptor.plugin_id not in _REGISTRY:
        _REGISTRY[descriptor.plugin_id] = descriptor


def unregister_plugin(plugin_id: str) -> None:
    _REGISTRY.pop(plugin_id, None)


def clear_registry() -> None:
    _REGISTRY.clear()
    _DISCOVERED.clear()


def collect_loaded_plugin_descriptors() -> None:
    for module_name in _KNOWN_PLUGIN_MODULES:
        if module_name not in sys.modules:
            continue
        registry_module_name = f"{module_name}.qguard_registry"
        if registry_module_name in _DISCOVERED:
            continue
        try:
            module = importlib.import_module(registry_module_name)
            get_descriptor = getattr(module, "get_qguard_descriptor", None)
            if callable(get_descriptor):
                register_plugin(get_descriptor())
        except Exception:
            continue
        finally:
            _DISCOVERED.add(registry_module_name)


def get_registered_plugins(*, discover: bool = True) -> tuple[PluginDescriptor, ...]:
    if discover:
        collect_loaded_plugin_descriptors()
    return tuple(sorted(_REGISTRY.values(), key=lambda item: (item.display_name, item.plugin_id)))


def get_plugin(plugin_id: str, *, discover: bool = True) -> PluginDescriptor | None:
    if discover:
        collect_loaded_plugin_descriptors()
    return _REGISTRY.get(plugin_id)


def visible_commands(
    descriptor: PluginDescriptor,
    role: QGuardRole,
    *,
    include_all: bool = False,
    permission_overrides: dict[str, QGuardRole] | None = None,
) -> list[CommandDescriptor]:
    commands = []
    for command in descriptor.commands:
        if not include_all and not command.show_in_help:
            continue
        required_role = _overridden_role(command, permission_overrides)
        if include_all or required_role <= role:
            commands.append(command)
    return commands


def build_help_text(
    role: QGuardRole = QGuardRole.MEMBER,
    *,
    query: str = "",
    include_all: bool = False,
) -> str:
    collect_loaded_plugin_descriptors()
    normalized_query = _normalize_query(query)
    if normalized_query in {"全部", "all"}:
        include_all = True
        normalized_query = ""

    plugins = _filtered_plugins(normalized_query)
    lines = ["QGuard 插件中心"]
    if include_all:
        lines[0] += "（全部命令）"
    if role is not None:
        lines.append(f"当前视图：{ROLE_LABELS.get(role, str(role))}")

    any_command = False
    for plugin in plugins:
        if not include_all and not plugin.show_in_help:
            continue
        commands = visible_commands(plugin, role, include_all=include_all)
        if not commands:
            continue
        any_command = True
        lines.extend(("", f"{plugin.display_name}："))
        for command in commands:
            lines.append(command.usage)

    if not any_command:
        lines.extend(("", "没有找到可展示的命令。"))
    elif not include_all:
        lines.extend(("", "更多：/管 帮助 全部，/管 插件"))
    return "\n".join(lines)


def build_plugin_list_text(role: QGuardRole = QGuardRole.MEMBER) -> str:
    plugins = get_registered_plugins()
    lines = ["QGuard 插件中心"]
    for plugin in plugins:
        commands = visible_commands(plugin, role)
        if not commands and not plugin.show_in_help:
            continue
        suffix = "默认开" if plugin.default_enabled else "默认关"
        lines.append(f"- {plugin.plugin_id}：{plugin.display_name}（{suffix}，命令 {len(commands)} 个）")
    lines.append("")
    lines.append("用法：/管 插件 状态，/管 插件 帮助 插件ID")
    return "\n".join(lines)


def build_plugin_help_text(plugin_id: str, role: QGuardRole = QGuardRole.MEMBER) -> str:
    plugin = get_plugin(plugin_id)
    if plugin is None:
        return f"没有找到插件：{plugin_id}"
    commands = visible_commands(plugin, role, include_all=True)
    lines = [f"{plugin.display_name}", plugin.description]
    if plugin.version:
        lines.append(f"版本：{plugin.version}")
    if commands:
        lines.append("")
        lines.append("命令：")
        for command in commands:
            role_label = ROLE_LABELS.get(command.required_role, str(command.required_role))
            lines.append(f"{command.usage} - {command.summary}（{role_label}+）")
    else:
        lines.append("暂无可展示命令。")
    return "\n".join(lines)


async def build_plugin_status_text(context: RegistryContext) -> str:
    plugins = get_registered_plugins()
    lines = ["插件中心状态"]
    for plugin in plugins:
        lines.append(await _plugin_status_line(plugin, context))
    return "\n".join(lines)


async def build_help_text_for_context(
    context: RegistryContext,
    *,
    query: str = "",
    include_all: bool = False,
) -> str:
    collect_loaded_plugin_descriptors()
    normalized_query = _normalize_query(query)
    if normalized_query in {"全部", "all"}:
        include_all = True
        normalized_query = ""

    configs = {}
    if context.group_id is not None:
        try:
            from nonebot_plugin_qguard.services.plugin_center_service import PluginCenterService

            configs = await PluginCenterService().configs_for_group(context.group_id)
        except Exception:
            configs = {}

    plugins = _filtered_plugins(normalized_query)
    lines = ["QGuard 插件中心"]
    if include_all:
        lines[0] += "（全部命令）"
    lines.append(f"当前视图：{ROLE_LABELS.get(context.role, str(context.role))}")

    any_command = False
    for plugin in plugins:
        config = configs.get(plugin.plugin_id)
        if not include_all and config is not None and config.enabled is False:
            continue
        if not include_all and not plugin.show_in_help:
            continue
        overrides = _permission_overrides_from_config(config)
        commands = visible_commands(plugin, context.role, include_all=include_all, permission_overrides=overrides)
        if not commands:
            continue
        any_command = True
        title = plugin.display_name
        if config is not None and config.enabled is False:
            title += "（插件中心已关闭）"
        lines.extend(("", f"{title}："))
        for command in commands:
            lines.append(command.usage)

    if not any_command:
        lines.extend(("", "没有找到可展示的命令。"))
    elif not include_all:
        lines.extend(("", "更多：/管 帮助 全部，/管 插件"))
    return "\n".join(lines)


async def build_single_plugin_status_text(plugin_id: str, context: RegistryContext) -> str:
    plugin = get_plugin(plugin_id)
    if plugin is None:
        return f"没有找到插件：{plugin_id}"
    return await _plugin_status_line(plugin, context)


async def _plugin_status_line(plugin: PluginDescriptor, context: RegistryContext) -> str:
    status = "已注册"
    if plugin.status_provider is not None:
        try:
            status = await _resolve_provider(plugin.status_provider, context)
        except Exception as exc:
            status = f"状态获取失败：{exc.__class__.__name__}"
    return f"{plugin.display_name}：{status}"


async def _resolve_provider(provider: StatusProvider, context: RegistryContext) -> str:
    result = provider(context)
    if inspect.isawaitable(result):
        result = await asyncio.wait_for(result, timeout=3)
    return str(result).strip() or "已注册"


async def resolve_group_enabled(plugin: PluginDescriptor, context: RegistryContext) -> bool | None:
    if plugin.group_enabled_provider is None:
        return None
    result = plugin.group_enabled_provider(context)
    if inspect.isawaitable(result):
        result = await asyncio.wait_for(result, timeout=3)
    if result is None:
        return None
    return bool(result)


async def set_group_enabled(plugin: PluginDescriptor, context: RegistryContext, enabled: bool) -> str:
    if plugin.group_enable_setter is None:
        raise NotImplementedError("plugin does not support group enable setter")
    result = plugin.group_enable_setter(context, enabled)
    if inspect.isawaitable(result):
        result = await asyncio.wait_for(result, timeout=5)
    return str(result).strip()


def _filtered_plugins(query: str) -> tuple[PluginDescriptor, ...]:
    plugins = get_registered_plugins(discover=False)
    if not query:
        return plugins
    result: list[PluginDescriptor] = []
    for plugin in plugins:
        haystacks = [plugin.plugin_id, plugin.display_name, plugin.module_name, plugin.description]
        haystacks.extend(CATEGORY_LABELS.get(command.category, command.category) for command in plugin.commands)
        haystacks.extend(command.command for command in plugin.commands)
        haystacks.extend(command.usage for command in plugin.commands)
        if any(query in item.lower() for item in haystacks):
            result.append(plugin)
    return tuple(result)


def _normalize_query(query: str) -> str:
    return query.strip().lower()


def parse_registry_role(text: str) -> QGuardRole:
    normalized = text.strip().lower()
    aliases = {
        "0": QGuardRole.MEMBER,
        "member": QGuardRole.MEMBER,
        "普通": QGuardRole.MEMBER,
        "普通成员": QGuardRole.MEMBER,
        "成员": QGuardRole.MEMBER,
        "1": QGuardRole.TRUSTED,
        "trusted": QGuardRole.TRUSTED,
        "可信": QGuardRole.TRUSTED,
        "可信用户": QGuardRole.TRUSTED,
        "信任": QGuardRole.TRUSTED,
        "2": QGuardRole.MINI_ADMIN,
        "mini": QGuardRole.MINI_ADMIN,
        "mini_admin": QGuardRole.MINI_ADMIN,
        "小管理": QGuardRole.MINI_ADMIN,
        "小管": QGuardRole.MINI_ADMIN,
        "3": QGuardRole.GROUP_ADMIN,
        "group_admin": QGuardRole.GROUP_ADMIN,
        "admin": QGuardRole.GROUP_ADMIN,
        "管理员": QGuardRole.GROUP_ADMIN,
        "群管理员": QGuardRole.GROUP_ADMIN,
        "4": QGuardRole.GROUP_OWNER,
        "group_owner": QGuardRole.GROUP_OWNER,
        "owner": QGuardRole.GROUP_OWNER,
        "群主": QGuardRole.GROUP_OWNER,
        "5": QGuardRole.SUPER_ADMIN,
        "super_admin": QGuardRole.SUPER_ADMIN,
        "super": QGuardRole.SUPER_ADMIN,
        "主人": QGuardRole.SUPER_ADMIN,
        "超级管理员": QGuardRole.SUPER_ADMIN,
    }
    if normalized not in aliases:
        raise ValueError("角色只支持：普通、可信、小管理、群管理员、群主、超级管理员。")
    return aliases[normalized]


def _overridden_role(command: CommandDescriptor, overrides: dict[str, QGuardRole] | None) -> QGuardRole:
    if not overrides:
        return command.required_role
    return overrides.get(command.usage, overrides.get(command.command, command.required_role))


def _permission_overrides_from_config(config) -> dict[str, QGuardRole]:
    if config is None:
        return {}
    try:
        raw = config.permission_overrides
    except AttributeError:
        return {}
    return {key: QGuardRole(value) for key, value in raw.items()}
