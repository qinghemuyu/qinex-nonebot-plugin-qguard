from dataclasses import dataclass
from uuid import uuid4

import pytest

from nonebot_plugin_support_bot.commands._common import parse_support_command
from nonebot_plugin_support_bot.config import Config, _parse_int_list
from nonebot_plugin_support_bot.models import init_db
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.schemas import SupportIntent
from nonebot_plugin_support_bot.services.support_service import SupportBotService
from nonebot_plugin_support_bot.services.ticket_service import TicketService


@dataclass
class FakeWikiResponse:
    answer: str
    references: list[str]
    ai_used: bool = False


@dataclass
class FakeDiagnosisResult:
    title: str = "缺少依赖"
    root_cause: str = "Python 环境缺少模块。"
    fix_steps: list[str] | None = None
    questions: list[str] | None = None


@dataclass
class FakeDiagnosis:
    result: FakeDiagnosisResult
    record_no: str = "D202606170001"
    ai_used: bool = False


class FakeIntegration:
    async def ask_wiki(self, question: str, *, group_id: int | None, user_id: int | None) -> FakeWikiResponse:
        return FakeWikiResponse(answer=f"知识库回答：{question}", references=["K0001"])

    async def diagnose_log(self, text: str, *, group_id: int | None, user_id: int | None) -> FakeDiagnosis:
        return FakeDiagnosis(
            result=FakeDiagnosisResult(
                fix_steps=["安装缺少的依赖。"],
                questions=["请确认 Python 版本。"],
            )
        )


def test_parse_support_command() -> None:
    assert parse_support_command("/客服 状态") == ("/客服", ["状态"], "")
    assert parse_support_command("/求助 压枪怎么配置") == ("/求助", [], "压枪怎么配置")
    assert parse_support_command("/工单 创建 映射没反应") == ("/工单", ["创建"], "映射没反应")
    assert parse_support_command("/管 状态") is None


def test_support_admin_env_parser() -> None:
    assert _parse_int_list("[1348984838]") == [1348984838]
    assert _parse_int_list("1,2,3") == [1, 2, 3]


@pytest.mark.asyncio
async def test_support_intent_rules() -> None:
    service = IntentService(Config())

    log_intent = await service.classify("Traceback ModuleNotFoundError: No module named x")
    short_intent = await service.classify("打不开")
    ticket_intent = await service.classify("授权激活失败")

    assert log_intent.should_diagnose_log
    assert short_intent.reply_strategy == "ask_followup"
    assert ticket_intent.should_create_ticket


@pytest.mark.asyncio
async def test_support_bot_wiki_answer() -> None:
    await init_db()
    group_id = 850000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    reply = await service.handle_user_issue("压枪怎么配置", group_id=group_id, user_id=1)

    assert "知识库回答" in reply.text
    assert reply.references == ["K0001"]
    assert reply.state == "waiting_user_feedback"


@pytest.mark.asyncio
async def test_support_bot_log_diagnosis() -> None:
    await init_db()
    group_id = 860000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    reply = await service.handle_user_issue(
        "Traceback ModuleNotFoundError: No module named x",
        group_id=group_id,
        user_id=1,
        force_log=True,
    )

    assert "诊断 D202606170001" in reply.text
    assert "安装缺少的依赖" in reply.text
    assert reply.diagnosis_no == "D202606170001"


@pytest.mark.asyncio
async def test_support_ticket_lifecycle() -> None:
    await init_db()
    group_id = 870000000 + (uuid4().int % 100000000)
    ticket_service = TicketService(Config())

    ticket = await ticket_service.create_ticket(
        description="映射没反应",
        group_id=group_id,
        user_id=123,
        intent=SupportIntent(issue_type="mapping_not_working"),
    )
    assigned = await ticket_service.assign_ticket(ticket.ticket_no, assignee_id=456)
    noted = await ticket_service.add_note(ticket.ticket_no, sender_id=456, sender_role="admin", content="已联系用户")
    closed = await ticket_service.set_status(ticket.ticket_no, "closed", operator_id=456)
    loaded, messages = await ticket_service.get_ticket(ticket.ticket_no)

    assert ticket.ticket_no.startswith("T")
    assert assigned is not None and assigned.status == "processing"
    assert noted is not None
    assert closed is not None and closed.status == "closed"
    assert loaded is not None and loaded.ticket_no == ticket.ticket_no
    assert len(messages) >= 4
