from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_ai_core.config import load_config
from nonebot_plugin_ai_core.exceptions import AICoreError
from nonebot_plugin_ai_core.service import AICoreService

from ._common import finish_reply, get_event_group_id, is_ai_core_admin

test_matcher = on_message(priority=5, block=False)


@test_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    text = event.get_plaintext().strip()
    prompt = parse_ai_test_prompt(text)
    if prompt is None:
        return

    config = load_config()
    if not is_ai_core_admin(event, config):
        await finish_reply(test_matcher, bot, event, "权限不足。")

    try:
        response = await AICoreService(config).chat(
            [
                {"role": "system", "content": "你是 AI Core 连通性测试助手。请用中文简短回答，不超过 80 字。"},
                {"role": "user", "content": prompt},
            ],
            user_id=event.user_id,
            group_id=get_event_group_id(event),
            purpose="ai_core_test",
            max_tokens=256,
            temperature=0.2,
        )
    except AICoreError as exc:
        await finish_reply(test_matcher, bot, event, f"AI Core 测试失败：{exc}")
    except Exception as exc:
        await finish_reply(test_matcher, bot, event, f"AI Core 测试失败：{exc}")

    await finish_reply(test_matcher, bot, event, f"AI Core 测试成功\n{response.strip()}")


def parse_ai_test_prompt(text: str) -> str | None:
    if text == "/ai测试":
        return "请回复：AI Core 已连通。"
    if text.startswith("/ai测试 "):
        prompt = text.removeprefix("/ai测试 ").strip()
        return prompt or "请回复：AI Core 已连通。"
    return None
