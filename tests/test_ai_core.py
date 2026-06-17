from dataclasses import dataclass
from uuid import uuid4

import pytest
from pydantic import BaseModel

from nonebot_plugin_ai_core.client.base import AIClientResponse
from nonebot_plugin_ai_core.config import Config
from nonebot_plugin_ai_core.exceptions import AIRateLimitExceeded
from nonebot_plugin_ai_core.models import init_db
from nonebot_plugin_ai_core.safety.mask import mask_text
from nonebot_plugin_ai_core.service import AICoreService
from nonebot_plugin_ai_core.utils.json_repair import parse_model_from_text


@dataclass
class FakeClient:
    response: str
    calls: int = 0

    async def chat(self, messages: list[dict], *, temperature: float, max_tokens: int) -> AIClientResponse:
        self.calls += 1
        return AIClientResponse(content=self.response, prompt_tokens=10, completion_tokens=5, total_tokens=15)


class DemoResult(BaseModel):
    label: str
    score: int


def test_mask_text_hides_sensitive_content() -> None:
    text = "sk-1234567890abcdef token=abcdef123456 user@qq.com 13800138000 1348984838"
    masked = mask_text(text)

    assert "sk-1234567890abcdef" not in masked
    assert "abcdef123456" not in masked
    assert "user@qq.com" not in masked
    assert "13800138000" not in masked
    assert "1348984838" not in masked


def test_parse_model_from_markdown_json() -> None:
    result = parse_model_from_text('```json\n{"label": "ok", "score": 9}\n```', DemoResult)

    assert result.label == "ok"
    assert result.score == 9


@pytest.mark.asyncio
async def test_ai_core_classify_and_cache() -> None:
    await init_db()
    client = FakeClient("bug")
    service = AICoreService(
        Config(ai_core_enable_cache=True, ai_core_global_daily_limit=0, ai_core_daily_limit_per_group=0, ai_core_daily_limit_per_user=0),
        client=client,
    )
    user_id = 900000000 + (uuid4().int % 100000000)
    text = f"程序打不开 {uuid4()}"

    first = await service.classify(text, ["bug", "usage"], user_id=user_id, group_id=1)
    second = await service.classify(text, ["bug", "usage"], user_id=user_id, group_id=1)

    assert first == "bug"
    assert second == "bug"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_ai_core_extract_json() -> None:
    await init_db()
    client = FakeClient('{"label": "ok", "score": 7}')
    service = AICoreService(
        Config(ai_core_enable_cache=False, ai_core_global_daily_limit=0, ai_core_daily_limit_per_group=0, ai_core_daily_limit_per_user=0),
        client=client,
    )

    result = await service.extract_json([{"role": "user", "content": "demo"}], DemoResult)

    assert result.label == "ok"
    assert result.score == 7


@pytest.mark.asyncio
async def test_ai_core_usage_summary() -> None:
    await init_db()
    service = AICoreService(
        Config(ai_core_enable_cache=False, ai_core_global_daily_limit=0, ai_core_daily_limit_per_group=0, ai_core_daily_limit_per_user=0),
        client=FakeClient("ok"),
    )

    await service.chat([{"role": "user", "content": f"summary {uuid4()}"}])
    summary = await service.usage_summary()

    assert summary["total_calls"] >= 1
    assert summary["success_calls"] >= 1


@pytest.mark.asyncio
async def test_ai_core_user_rate_limit() -> None:
    await init_db()
    user_id = 910000000 + (uuid4().int % 100000000)
    service = AICoreService(
        Config(ai_core_enable_cache=False, ai_core_daily_limit_per_user=1, ai_core_daily_limit_per_group=0, ai_core_global_daily_limit=0),
        client=FakeClient("ok"),
    )

    await service.chat([{"role": "user", "content": "hello"}], user_id=user_id, group_id=1)

    with pytest.raises(AIRateLimitExceeded):
        await service.chat([{"role": "user", "content": "hello again"}], user_id=user_id, group_id=1)
