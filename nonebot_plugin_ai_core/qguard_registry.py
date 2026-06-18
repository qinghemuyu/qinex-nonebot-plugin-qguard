from __future__ import annotations

from nonebot_plugin_ai_core.config import load_config
from nonebot_plugin_ai_core.service import AICoreService
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, RegistryContext, register_plugin


async def _status_provider(context: RegistryContext) -> str:
    config = load_config()
    summary = await AICoreService(config).usage_summary()
    cache_state = "开" if config.ai_core_enable_cache else "关"
    return (
        f"Provider {config.ai_core_provider}，Model {config.ai_core_model}，缓存 {cache_state}，"
        f"今日 {summary['total_calls']} 次，成功 {summary['success_calls']}，失败 {summary['failed_calls']}，"
        f"tokens {summary['total_tokens']}"
    )


def get_qguard_descriptor() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="ai_core",
        display_name="AI Core",
        module_name="nonebot_plugin_ai_core",
        description="统一 AI 模型接入、缓存、限流、脱敏和调用统计。",
        commands=(
            CommandDescriptor(
                command="/ai状态",
                summary="查看 AI Core 状态和今日调用统计",
                usage="/ai状态",
                category="ai",
                required_role=QGuardRole.SUPER_ADMIN,
                reply_category="command_reply",
            ),
            CommandDescriptor(
                command="/ai测试",
                summary="真实调用模型测试 API 配置",
                usage="/ai测试",
                category="ai",
                required_role=QGuardRole.SUPER_ADMIN,
                examples=("/ai测试 用一句话介绍你自己",),
                reply_category="command_reply",
            ),
        ),
        default_enabled=True,
        status_provider=_status_provider,
    )


def register_with_qguard() -> None:
    register_plugin(get_qguard_descriptor())
