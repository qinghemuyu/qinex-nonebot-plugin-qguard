from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_ai_core.config import load_config
from nonebot_plugin_ai_core.service import AICoreService

from ._common import check_qguard_command_permission, finish_reply, is_ai_core_admin

status_matcher = on_message(priority=5, block=False)


@status_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    text = event.get_plaintext().strip()
    if text != "/ai状态":
        return
    config = load_config()
    permission_check = await check_qguard_command_permission(
        bot,
        event,
        selector="/ai状态",
        fallback_role=5,
    )
    if permission_check.denied_reason:
        await finish_reply(status_matcher, bot, event, permission_check.denied_reason)
    if not permission_check.checked and not is_ai_core_admin(event, config):
        await finish_reply(status_matcher, bot, event, "权限不足。")
    summary = await AICoreService(config).usage_summary()
    cache_state = "开启" if config.ai_core_enable_cache else "关闭"
    await finish_reply(
        status_matcher,
        bot,
        event,
        "AI Core 状态\n"
        f"Provider：{config.ai_core_provider}\n"
        f"Model：{config.ai_core_model}\n"
        f"缓存：{cache_state}\n"
        f"今日调用：{summary['total_calls']} 次，成功 {summary['success_calls']} 次，失败 {summary['failed_calls']} 次\n"
        f"今日估算 tokens：{summary['total_tokens']}"
    )
