from dataclasses import dataclass
from uuid import uuid4

import pytest

from nonebot_plugin_support_bot.commands._common import parse_support_command
from nonebot_plugin_support_bot.config import Config, _parse_int_list
from nonebot_plugin_support_bot.models import init_db
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.support_service import SupportBotService


@dataclass
class FakeWikiResponse:
    answer: str
    references: list[str]
    ai_used: bool = False


class FakeIntegration:
    def __init__(self, references: list[str] | None = None) -> None:
        self.references = references if references is not None else ["K0001"]

    async def ask_wiki(self, question: str, *, group_id: int | None, user_id: int | None) -> FakeWikiResponse:
        return FakeWikiResponse(answer=f"知识库回答：{question}", references=self.references)


def test_parse_support_command() -> None:
    assert parse_support_command("/客服 状态") == ("/客服", ["状态"], "")
    assert parse_support_command("/求助 压枪怎么配置") == ("/求助", [], "压枪怎么配置")
    assert parse_support_command("/工单 创建 映射没反应") is None
    assert parse_support_command("/报错 xxx") is None
    assert parse_support_command("/管 状态") is None


def test_support_admin_env_parser() -> None:
    assert _parse_int_list("[1348984838]") == [1348984838]
    assert _parse_int_list("1,2,3") == [1, 2, 3]


@pytest.mark.asyncio
async def test_support_intent_rules_are_knowledge_only() -> None:
    service = IntentService(Config())

    log_intent = await service.classify("Traceback ModuleNotFoundError: No module named x")
    short_intent = await service.classify("打不开")
    license_intent = await service.classify("授权激活失败怎么处理")

    assert log_intent.should_search_wiki
    assert short_intent.reply_strategy == "ask_followup"
    assert license_intent.should_search_wiki


@pytest.mark.asyncio
async def test_support_bot_wiki_answer() -> None:
    await init_db()
    group_id = 850000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    reply = await service.handle_user_issue("压枪怎么配置", group_id=group_id, user_id=1)

    assert "知识库回答" in reply.text
    assert reply.references == ["K0001"]
    assert reply.state == "answered"


@pytest.mark.asyncio
async def test_support_bot_no_answer_in_current_scope() -> None:
    await init_db()
    group_id = 860000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration(references=[]))

    reply = await service.handle_user_issue("不在知识范围的问题", group_id=group_id, user_id=1)

    assert "当前群生效的知识库范围" in reply.text
    assert reply.state == "no_answer"
