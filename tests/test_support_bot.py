from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import select

from nonebot_plugin_group_wiki.models import init_db as init_wiki_db
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_support_bot.commands._common import parse_support_command
from nonebot_plugin_support_bot.config import Config, _parse_int_list
from nonebot_plugin_support_bot.models import SupportGroupConfig, SupportIssueCluster, SupportNoAnswer, get_session, init_db
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.support_service import SupportBotService


@dataclass
class FakeWikiResponse:
    answer: str
    references: list[str]
    ai_used: bool = False


class FakeIntegration:
    def __init__(self, references: list[str] | None = None) -> None:
        self.references = references if references is not None else ["06_连点与压枪#压枪"]
        self.questions: list[str] = []
        self.search_queries: list[str | None] = []
        self.casual_questions: list[str] = []

    async def ask_wiki(
        self,
        question: str,
        *,
        group_id: int | None,
        user_id: int | None,
        search_query: str | None = None,
    ) -> FakeWikiResponse:
        self.questions.append(question)
        self.search_queries.append(search_query)
        return FakeWikiResponse(answer=f"知识库回答：{question}", references=self.references)

    async def casual_chat(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int | None,
        software_name: str,
        max_tokens: int,
    ) -> str:
        self.casual_questions.append(text)
        return f"闲聊回复：{text}"


def test_parse_support_command() -> None:
    assert parse_support_command("/客服 状态") == ("/客服", ["状态"], "")
    assert parse_support_command("/客服 补知识 N000001 先检查配置") == ("/客服", ["补知识"], "N000001 先检查配置")
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
    s3_activation = await service.classify("S3板子要怎么激活")
    blocked_license = await service.classify("S3板子授权码怎么破解")
    pc_jank = await service.classify("最新版上位机有那种掉帧的感觉，有时候一卡一卡的")
    panel_blank = await service.classify("上位机配置面板空白打不开")
    no_touch = await service.classify("保存了但是游戏里没有触点")
    ambiguous_mouse = await service.classify("鼠标没反应")
    vague_jank = await service.classify("卡")
    precise_calibration = await service.classify("校准映射之后 部分映射按键失效")
    p4_screen_jank = await service.classify("P4卡顿 投屏卡顿")
    wasd_component = await service.classify("按住WA再按D没反应")
    ads_component = await service.classify("右键开镜怎么配")
    generic_wasd = await service.classify("我的wasd键盘坏了怎么办")
    generic_game = await service.classify("王者荣耀怎么走位")
    out_scope = await service.classify("Python 怎么安装依赖")

    assert log_intent.reply_strategy == "reject"
    assert short_intent.reply_strategy == "ask_followup"
    assert license_intent.reply_strategy == "safe_no_answer"
    assert s3_activation.reply_strategy == "answer"
    assert s3_activation.issue_type == "activation_usage"
    assert blocked_license.reply_strategy == "safe_no_answer"
    assert pc_jank.reply_strategy == "answer"
    assert pc_jank.issue_type == "performance_problem"
    assert panel_blank.reply_strategy == "answer"
    assert panel_blank.issue_type == "launch_failed"
    assert no_touch.reply_strategy == "answer"
    assert no_touch.issue_type == "mapping_not_working"
    assert ambiguous_mouse.reply_strategy == "ask_followup"
    assert "S3" in " ".join(ambiguous_mouse.missing_fields)
    assert vague_jank.reply_strategy == "ask_followup"
    assert vague_jank.issue_type == "performance_problem"
    assert precise_calibration.reply_strategy == "answer"
    assert p4_screen_jank.reply_strategy == "answer"
    assert p4_screen_jank.issue_type == "screenhub_usage"
    assert wasd_component.reply_strategy == "answer"
    assert wasd_component.issue_type == "mapping_not_working"
    assert ads_component.reply_strategy == "answer"
    assert ads_component.issue_type == "config_problem"
    assert generic_wasd.reply_strategy == "casual_chat"
    assert generic_game.reply_strategy == "casual_chat"
    assert out_scope.reply_strategy == "casual_chat"


@pytest.mark.asyncio
async def test_support_intent_can_disable_casual_chat() -> None:
    service = IntentService(Config(support_bot_allow_casual_chat=False))

    out_scope = await service.classify("Python 怎么安装依赖")

    assert out_scope.reply_strategy == "reject"


@pytest.mark.asyncio
async def test_support_bot_wiki_answer() -> None:
    await init_db()
    group_id = 850000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    reply = await service.handle_user_issue("压枪怎么配置", group_id=group_id, user_id=1)

    assert "知识库回答" in reply.text
    assert reply.references == ["06_连点与压枪#压枪"]
    assert reply.state == "answered"


@pytest.mark.asyncio
async def test_support_bot_low_confidence_jank_asks_diagnostic_question() -> None:
    await init_db()
    group_id = 850200000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    reply = await service.handle_user_issue("卡", group_id=group_id, user_id=1)

    assert reply.state == "collecting_issue"
    assert "卡顿/不跟手" in reply.text
    assert "滑屏、投屏画面，还是按键响应" in reply.text


@pytest.mark.asyncio
async def test_support_bot_allows_safe_s3_activation_question() -> None:
    await init_db()
    group_id = 850500000 + (uuid4().int % 100000000)
    integration = FakeIntegration(references=["11_激活与安全说明#S3 硬件板子怎么激活"])
    service = SupportBotService(Config(), integration_service=integration)

    reply = await service.handle_user_issue("S3板子要怎么激活", group_id=group_id, user_id=1)

    assert reply.state == "answered"
    assert reply.references == ["11_激活与安全说明#S3 硬件板子怎么激活"]
    assert integration.questions == ["S3板子要怎么激活"]


@pytest.mark.asyncio
async def test_support_bot_allows_pc_client_jank_question() -> None:
    await init_db()
    group_id = 850600000 + (uuid4().int % 100000000)
    integration = FakeIntegration(references=["10_排障与卡顿速查#卡顿分三段"])
    service = SupportBotService(Config(), integration_service=integration)

    question = "最新版上位机有那种掉帧的感觉，有时候一卡一卡的"
    reply = await service.handle_user_issue(question, group_id=group_id, user_id=1)

    assert reply.state == "answered"
    assert reply.references == ["10_排障与卡顿速查#卡顿分三段"]
    assert integration.questions == [question]


@pytest.mark.asyncio
async def test_support_bot_p4_screenhub_jank_answers_instead_of_followup() -> None:
    await init_db()
    group_id = 850700000 + (uuid4().int % 100000000)
    integration = FakeIntegration(references=["07_投屏ScreenHub#投屏卡顿怎么办"])
    service = SupportBotService(Config(), integration_service=integration)

    question = "P4卡顿 投屏卡顿"
    reply = await service.handle_user_issue(question, group_id=group_id, user_id=1)

    assert reply.state == "answered"
    assert reply.references == ["07_投屏ScreenHub#投屏卡顿怎么办"]
    assert integration.questions == [question]


@pytest.mark.asyncio
async def test_support_bot_continues_recent_user_context() -> None:
    await init_db()
    group_id = 851000000 + (uuid4().int % 100000000)
    integration = FakeIntegration()
    service = SupportBotService(Config(support_bot_conversation_ttl_seconds=180), integration_service=integration)

    first = await service.handle_user_issue("QInEX 滑屏卡顿怎么办", group_id=group_id, user_id=1)
    assert first.state == "answered"

    assert await service.should_handle_continuation("还是不行", group_id=group_id, user_id=1)
    assert not await service.should_handle_continuation("还是不行", group_id=group_id, user_id=2)
    assert not await service.should_handle_continuation("谢谢", group_id=group_id, user_id=1)
    assert not await service.should_handle_continuation("哈哈哈", group_id=group_id, user_id=1)
    assert not await service.should_handle_continuation("有", group_id=group_id, user_id=1)
    assert not await service.should_handle_continuation("卡", group_id=group_id, user_id=1)
    assert await service.should_handle_continuation("还卡", group_id=group_id, user_id=1)

    second = await service.handle_user_issue("还是不行", group_id=group_id, user_id=1)

    assert second.state == "answered"
    assert len(integration.questions) == 2
    assert "上一轮问题" in integration.questions[-1]
    assert "滑屏卡顿" in integration.questions[-1]
    assert "还是不行" in integration.questions[-1]
    assert integration.search_queries[-1] is not None
    assert "滑屏卡顿" in integration.search_queries[-1]
    assert "还是不行" in integration.search_queries[-1]
    assert "请基于当前群可用知识库" not in integration.search_queries[-1]


@pytest.mark.asyncio
async def test_support_bot_escalates_long_unresolved_issue_once() -> None:
    await init_db()
    group_id = 851500000 + (uuid4().int % 100000000)
    integration = FakeIntegration()
    service = SupportBotService(
        Config(support_bot_conversation_ttl_seconds=180, support_bot_unresolved_escalation_turns=3),
        integration_service=integration,
    )

    first = await service.handle_user_issue("QInEX 滑屏卡顿怎么办", group_id=group_id, user_id=1)
    second = await service.handle_user_issue("还是不行", group_id=group_id, user_id=1)
    third = await service.handle_user_issue("还是不行", group_id=group_id, user_id=1)

    assert not first.owner_escalation
    assert not second.owner_escalation
    assert third.owner_escalation
    assert third.owner_escalation_turns == 3
    assert "连续未解决" in third.owner_escalation_summary
    assert "QInEX 滑屏卡顿怎么办" in third.owner_escalation_summary
    assert "最近补充" in third.owner_escalation_summary

    await service.mark_issue_escalation_notified(group_id, 1)
    fourth = await service.handle_user_issue("还是不行", group_id=group_id, user_id=1)

    assert not fourth.owner_escalation


@pytest.mark.asyncio
async def test_support_bot_resolved_feedback_updates_issue_cluster() -> None:
    await init_db()
    group_id = 851700000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    first = await service.handle_user_issue("QInEX 滑屏卡顿怎么办", group_id=group_id, user_id=1)
    second = await service.handle_user_issue("解决了", group_id=group_id, user_id=1)

    async with get_session() as session:
        result = await session.scalars(select(SupportIssueCluster))
        clusters = list(result)

    assert first.state == "answered"
    assert second.state == "resolved_feedback"
    assert "已解决" in second.text
    assert any(item.resolved_count >= 1 for item in clusters)


@pytest.mark.asyncio
async def test_support_bot_continuation_rule_does_not_create_group_config() -> None:
    await init_db()
    group_id = 852000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    assert not await service.should_handle_continuation("还是不行", group_id=group_id, user_id=1)

    async with get_session() as session:
        result = await session.scalars(
            select(SupportGroupConfig).where(SupportGroupConfig.group_id == group_id)
        )
        item = result.one_or_none()

    assert item is None


@pytest.mark.asyncio
async def test_answer_bot_allows_casual_chat_for_non_qinex_question() -> None:
    await init_db()
    group_id = 855000000 + (uuid4().int % 100000000)
    integration = FakeIntegration()
    service = SupportBotService(Config(), integration_service=integration)

    reply = await service.handle_user_issue("Python 怎么安装依赖", group_id=group_id, user_id=1)

    assert "闲聊回复" in reply.text
    assert reply.state == "casual_chat"
    assert integration.casual_questions == ["Python 怎么安装依赖"]


@pytest.mark.asyncio
async def test_support_bot_harassment_adds_score_delta_for_abuse() -> None:
    await init_db()
    group_id = 856000000 + (uuid4().int % 100000000)
    service = SupportBotService(
        Config(support_bot_harassment_score_threshold=3, support_bot_harassment_score_cooldown_seconds=0),
        integration_service=FakeIntegration(),
    )

    reply = await service.handle_user_issue("垃圾机器人", group_id=group_id, user_id=456)

    assert reply.state == "out_of_scope"
    assert reply.harassment_reason == "辱骂智能客服"
    assert reply.harassment_score_delta == 1
    assert "交给群管积分处理" in reply.text


@pytest.mark.asyncio
async def test_support_bot_casual_chat_does_not_accumulate_mild_out_of_scope() -> None:
    await init_db()
    group_id = 856500000 + (uuid4().int % 100000000)
    service = SupportBotService(
        Config(support_bot_harassment_score_threshold=2, support_bot_harassment_score_cooldown_seconds=0),
        integration_service=FakeIntegration(),
    )

    first = await service.handle_user_issue("天气怎么样", group_id=group_id, user_id=457)
    second = await service.handle_user_issue("讲个笑话", group_id=group_id, user_id=457)

    assert first.harassment_score_delta == 0
    assert second.harassment_score_delta == 0
    assert first.state == "casual_chat"
    assert second.state == "casual_chat"


@pytest.mark.asyncio
async def test_support_bot_harassment_ignores_owner() -> None:
    await init_db()
    group_id = 856800000 + (uuid4().int % 100000000)
    service = SupportBotService(
        Config(support_bot_harassment_score_threshold=3, support_bot_harassment_score_cooldown_seconds=0),
        integration_service=FakeIntegration(),
    )

    reply = await service.handle_user_issue("垃圾机器人", group_id=group_id, user_id=1348984838)

    assert reply.harassment_score_delta == 0
    assert "群管积分" not in reply.text


@pytest.mark.asyncio
async def test_support_bot_no_answer_in_current_scope() -> None:
    await init_db()
    group_id = 860000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration(references=[]))

    reply = await service.handle_user_issue("QInEX 不在知识范围的问题", group_id=group_id, user_id=1)

    assert "当前群生效的知识库范围" in reply.text
    assert reply.state == "no_answer"
    assert reply.no_answer_id.startswith("N")

    async with get_session() as session:
        result = await session.scalars(select(SupportIssueCluster))
        clusters = list(result)

    assert any(item.no_answer_count >= 1 for item in clusters)
    gaps = await service.issue_gaps()
    assert "缺口看板" in gaps
    assert "优先处理" in gaps
    assert "C000" in gaps
    assert "下一步：/客服 补知识" in gaps


@pytest.mark.asyncio
async def test_support_bot_records_no_answer() -> None:
    await init_db()
    group_id = 870000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration(references=[]))

    reply = await service.handle_user_issue("QInEX 某个知识库没有的问题", group_id=group_id, user_id=123)

    async with get_session() as session:
        item = await session.get(SupportNoAnswer, int(reply.no_answer_id.removeprefix("N")))

    assert item is not None
    assert item.group_id == group_id
    assert item.user_id == 123
    assert "QInEX" in item.question


@pytest.mark.asyncio
async def test_support_bot_supplement_no_answer_creates_wiki_article() -> None:
    await init_db()
    await init_wiki_db()
    group_id = 875000000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration(references=[]))

    reply = await service.handle_user_issue("QInEX 某个补知识测试问题", group_id=group_id, user_id=123)
    result = await service.supplement_no_answer(
        reply.no_answer_id,
        "先确认当前群知识范围包含 FAQ,然后按软件提示检查配置。",
        author_id=1348984838,
        group_id=group_id,
    )
    hits = await WikiSearchService().search("补知识测试问题", group_id=group_id)

    assert "已补充知识" in result
    assert hits
    assert hits[0].article.source_ref_id == reply.no_answer_id


@pytest.mark.asyncio
async def test_support_bot_supplement_issue_cluster_creates_wiki_article() -> None:
    await init_db()
    await init_wiki_db()
    group_id = 875500000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    await service.handle_user_issue("上位机遮罩打开了键盘同步输出到电脑", group_id=group_id, user_id=123)
    async with get_session() as session:
        result = await session.scalars(
            select(SupportIssueCluster)
            .where(SupportIssueCluster.last_group_id == group_id)
            .order_by(SupportIssueCluster.id.desc())
        )
        cluster = result.first()

    assert cluster is not None
    cluster_ref = f"C{cluster.id:06d}"
    result = await service.supplement_no_answer(
        cluster_ref,
        "上位机暂时没有屏蔽键盘同步输出到电脑的功能,建议先用游戏内输入设置或系统层方案规避。",
        author_id=1348984838,
        group_id=group_id,
    )
    hits = await WikiSearchService().search("遮罩 键盘 同步输出", group_id=group_id)

    assert "已补充知识" in result
    assert hits
    assert hits[0].article.source_type == "support_issue_cluster"
    assert hits[0].article.source_ref_id == cluster_ref


@pytest.mark.asyncio
async def test_support_bot_supplement_issue_cluster_by_display_title() -> None:
    await init_db()
    await init_wiki_db()
    group_id = 875700000 + (uuid4().int % 100000000)
    service = SupportBotService(Config(), integration_service=FakeIntegration())

    await service.handle_user_issue("QInEX 一个完全新的测试问题", group_id=group_id, user_id=123)
    async with get_session() as session:
        result = await session.scalars(
            select(SupportIssueCluster)
            .where(SupportIssueCluster.last_group_id == group_id)
            .order_by(SupportIssueCluster.id.desc())
        )
        cluster = result.first()

    assert cluster is not None
    result = await service.supplement_no_answer(
        cluster.title,
        "这是通过缺口看板旧版标题补充的答案。",
        author_id=1348984838,
        group_id=group_id,
    )

    assert "已补充知识" in result
