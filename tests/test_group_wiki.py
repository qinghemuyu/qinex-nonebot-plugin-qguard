from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from nonebot_plugin_group_wiki.commands._common import parse_wiki_command
from nonebot_plugin_group_wiki.commands.root import parse_title_content
from nonebot_plugin_group_wiki.config import Config
from nonebot_plugin_group_wiki.models import init_db
from nonebot_plugin_group_wiki.services.article_service import GroupWikiService
from nonebot_plugin_group_wiki.services.import_service import ImportService
from nonebot_plugin_group_wiki.services.rag_service import RAGService, _build_knowledge_context, _clean_chat_answer
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService, expand_search_query
from nonebot_plugin_group_wiki.services.skill_registry import (
    COMPONENT_CATEGORY,
    FAQ_CATEGORY,
    TERMS_CATEGORY,
    categories_for_skill_ids,
    faq_chunk_allowed_for_categories,
    is_qinex_related,
    match_skill_id,
)
from nonebot_plugin_group_wiki.services.scope_service import WikiScopeService
from nonebot_plugin_group_wiki.utils.markdown import category_from_path, title_from_markdown
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


@dataclass
class FakeAICore:
    calls: int = 0

    async def chat(self, messages: list[dict], **kwargs) -> str:
        self.calls += 1
        assert "猫娘客服" in messages[0]["content"]
        assert "上位机" in messages[0]["content"]
        assert "不要 Markdown" in messages[0]["content"]
        assert "引用：文件名#小节" in messages[0]["content"]
        assert "知识库片段" in messages[-1]["content"]
        assert kwargs["temperature"] == 0.6
        return "喵，优先判断是配置没有保存或输出模式没选对。先保存配置，再检查输出模式。\n引用：06_连点与压枪#压枪"


@dataclass
class FakeSearchService:
    last_query: str = ""

    async def search(self, query: str, *, group_id: int | None = None, limit: int = 5) -> list:
        self.last_query = query
        return []


def test_parse_wiki_command() -> None:
    assert parse_wiki_command("/知识 搜索 压枪") == ("/知识", ["搜索"], "压枪")
    assert parse_wiki_command("/问 怎么压枪") == ("/问", [], "怎么压枪")
    assert parse_wiki_command("/管 状态") is None


def test_parse_title_content() -> None:
    assert parse_title_content("标题 内容 abc") == ("标题", "内容 abc")
    assert parse_title_content("only") == ("", "")


def test_markdown_helpers_and_splitter() -> None:
    assert title_from_markdown("# 标题\n正文", "fallback") == "标题"
    assert category_from_path(type("P", (), {"stem": "06_连点与压枪"})()) == "06_连点与压枪"
    assert split_text("abcdef", chunk_size=3, overlap=1) == ["abc", "cde", "ef"]


def test_qinex_skill_registry() -> None:
    categories, rejected = categories_for_skill_ids(["qinex_recoil_click", "qinex_p4", "qinex_activation"])
    term_categories, term_rejected = categories_for_skill_ids(["qinex_terms"])
    mapping_categories, mapping_rejected = categories_for_skill_ids(["qinex_mapping"])

    assert "06_连点与压枪" in categories
    assert "08_P4单机版" in categories
    assert "11_激活与安全说明" in categories
    assert TERMS_CATEGORY in term_categories
    assert COMPONENT_CATEGORY in mapping_categories
    assert FAQ_CATEGORY not in categories
    assert rejected == []
    assert term_rejected == []
    assert mapping_rejected == []
    assert match_skill_id("P4 单机版怎么用手机配置") == "qinex_p4"
    assert match_skill_id("S3板子要怎么激活") == "qinex_activation"
    assert match_skill_id("最新版上位机有时候一卡一卡的") == "qinex_troubleshooting"
    assert match_skill_id("上位机是什么意思") == "qinex_terms"
    assert match_skill_id("校准映射之后 部分映射按键失效") in {"qinex_mapping", "qinex_troubleshooting"}
    assert faq_chunk_allowed_for_categories("## 五、连点 / 压枪\n压枪怎么开", ["06_连点与压枪"])
    assert not faq_chunk_allowed_for_categories("## 七、投屏\n投屏怎么开", ["06_连点与压枪"])


def test_qinex_related_uses_context_for_weak_mapping_terms() -> None:
    assert is_qinex_related("按住WA再按D没反应")
    assert is_qinex_related("WASD走位映射怎么设置")
    assert is_qinex_related("右键开镜怎么配")
    assert is_qinex_related("视角太飘怎么调")
    assert is_qinex_related("校准映射之后 部分映射按键失效")
    assert not is_qinex_related("我的wasd键盘坏了怎么办")
    assert not is_qinex_related("王者荣耀怎么走位")


def test_clean_chat_answer_removes_markdown() -> None:
    raw = "## 结论\n**先保存配置**\n- 检查输出模式\n1. 重启 QInEX\n```text\n点保存\n```\n引用：[06](x)"
    cleaned = _clean_chat_answer(raw)

    assert "##" not in cleaned
    assert "**" not in cleaned
    assert "```" not in cleaned
    assert "- " not in cleaned
    assert "1. " not in cleaned
    assert "先保存配置" in cleaned
    assert "点保存" in cleaned
    assert "1）重启 QInEX" in cleaned


def test_build_knowledge_context_keeps_matched_chunk() -> None:
    chunk = "## 滑屏卡顿\n常见原因是回报率过高、异步设置不合适，先降低回报率，再检查控制模式。"
    hit = SimpleNamespace(
        reference="10_排障与卡顿速查#滑屏卡顿",
        article=SimpleNamespace(title="排障与卡顿速查", summary=""),
        snippet="常见原因是回报率过高",
        chunk_text=chunk,
    )

    context = _build_knowledge_context([hit])

    assert "片段1 [10_排障与卡顿速查#滑屏卡顿]" in context
    assert "回报率过高" in context
    assert "检查控制模式" in context


def test_expand_search_query_for_pc_client_jank() -> None:
    expanded = expand_search_query("最新版上位机有那种掉帧的感觉，有时候一卡一卡的")

    assert "映射软件" in expanded
    assert "PC端" in expanded
    assert "卡顿" in expanded
    assert "回报率" in expanded


def test_expand_search_query_for_common_support_phrases() -> None:
    no_touch = expand_search_query("上位机保存了但是游戏里没有触点")
    launch = expand_search_query("配置面板空白打不开")
    ads = expand_search_query("开镜灵敏度ADS开了但是右键不开镜")
    layer = expand_search_query("按键层里为什么不能改摇杆视角")
    calibration = expand_search_query("校准映射之后 部分映射按键失效")

    assert "保存配置" in no_touch
    assert "管理员权限" in no_touch
    assert "WebView2" in launch
    assert "完整解压" in launch
    assert "开镜触点" in ads
    assert "扩展层" in layer
    assert "触摸校准" in calibration
    assert "参考分辨率" in calibration
    assert "黑边" in calibration
    assert "坐标偏移" in calibration


@pytest.mark.asyncio
async def test_rag_uses_clean_search_query() -> None:
    search = FakeSearchService()

    await RAGService(Config(group_wiki_enable_ai=False), search_service=search).ask(
        "这是带连续对话元信息的问题",
        group_id=1,
        user_id=1,
        search_query="滑屏卡顿 还是不行",
    )

    assert search.last_query == "滑屏卡顿 还是不行"


@pytest.mark.asyncio
async def test_group_wiki_add_search_ask_and_feedback() -> None:
    await init_db()
    group_id = 830000000 + (uuid4().int % 100000000)
    service = GroupWikiService(Config(group_wiki_enable_ai=False, group_wiki_default_scope="global"))
    article = await service.add_article(
        title="压枪设置",
        content="压枪组件默认关闭。开启后从 0.002 到 0.01 小强度开始,并配合抖动。",
        group_id=group_id,
        author_id=1,
    )

    hits = await WikiSearchService().search("压枪", group_id=group_id)
    response = await RAGService(
        Config(group_wiki_enable_ai=True),
        ai_core=FakeAICore(),
    ).ask("怎么压枪", group_id=group_id, user_id=1)
    ok = await service.feedback(article.article_no, feedback_type="useful", group_id=group_id, user_id=1)

    assert hits
    assert hits[0].article.article_no == article.article_no
    assert response.references == [article.article_no]
    assert "优先判断" in response.answer
    assert ok


@pytest.mark.asyncio
async def test_group_wiki_local_import(tmp_path) -> None:
    await init_db()
    doc = tmp_path / "01_demo.md"
    doc.write_text("# Demo 文档\n\nQInEX 支持 S3 硬件模式。", encoding="utf-8")

    created, updated, skipped = await ImportService(Config(group_wiki_import_dir=str(tmp_path))).import_local_markdown(
        author_id=1
    )
    created_again, updated_again, skipped_again = await ImportService(
        Config(group_wiki_import_dir=str(tmp_path))
    ).import_local_markdown(author_id=1)
    hits = await WikiSearchService().search("S3")

    assert created >= 1
    assert updated >= 0
    assert skipped == 0
    assert (created_again, updated_again, skipped_again) == (0, 0, 1)
    assert any(hit.article.title == "Demo 文档" for hit in hits)
    assert any(hit.article.category == "01_demo" for hit in hits)


@pytest.mark.asyncio
async def test_group_wiki_reimport_updates_category_when_filename_policy_changes(tmp_path) -> None:
    await init_db()
    service = GroupWikiService(Config(group_wiki_enable_ai=False, group_wiki_default_scope="global"))
    await service.add_article(
        title="连点与压枪",
        content="# 连点与压枪\n\n压枪说明。",
        group_id=None,
        author_id=1,
        category="连点与压枪",
        source_type="import",
        source_ref_id="06_连点与压枪.md",
    )
    doc = tmp_path / "06_连点与压枪.md"
    doc.write_text("# 连点与压枪\n\n压枪说明。", encoding="utf-8")

    created, updated, skipped = await ImportService(Config(group_wiki_import_dir=str(tmp_path))).import_local_markdown(
        author_id=1
    )
    hits = await WikiSearchService().search("压枪")

    assert (created, updated, skipped) == (0, 1, 0)
    assert any(hit.article.category == "06_连点与压枪" for hit in hits)


@pytest.mark.asyncio
async def test_group_wiki_group_scope_filters_categories() -> None:
    await init_db()
    group_id = 845000000 + (uuid4().int % 100000000)
    service = GroupWikiService(Config(group_wiki_enable_ai=False, group_wiki_default_scope="global"))
    recoil = await service.add_article(
        title="压枪设置",
        content="压枪需要先开启压枪组件。",
        group_id=group_id,
        author_id=1,
        category="压枪",
    )
    mirror = await service.add_article(
        title="投屏设置",
        content="投屏需要使用 ScreenHub。",
        group_id=group_id,
        author_id=1,
        category="投屏",
    )

    accepted, rejected = await WikiScopeService().set_categories(group_id, ["压枪", "不存在"], updated_by=1)
    recoil_hits = await WikiSearchService().search("压枪", group_id=group_id)
    mirror_hits = await WikiSearchService().search("投屏", group_id=group_id)
    allowed, categories = await WikiScopeService().get_group_scope(group_id)

    assert accepted == ["压枪"]
    assert rejected == ["不存在"]
    assert recoil_hits and recoil_hits[0].article.article_no == recoil.article_no
    assert not any(hit.article.article_no == mirror.article_no for hit in mirror_hits)
    assert allowed == ["压枪"]
    assert {"压枪", "投屏"}.issubset(set(categories))


@pytest.mark.asyncio
async def test_group_wiki_faq_chunks_respect_scope() -> None:
    await init_db()
    group_id = 846000000 + (uuid4().int % 100000000)
    service = GroupWikiService(Config(group_wiki_enable_ai=False, group_wiki_default_scope="global"))
    faq = await service.add_article(
        title="QInEX 常见问题",
        content="# QInEX 常见问题\n\n## 五、连点 / 压枪\n压枪怎么开。\n\n## 七、投屏\n投屏怎么开。",
        group_id=group_id,
        author_id=1,
        category=FAQ_CATEGORY,
    )
    await service.add_article(
        title="连点与压枪",
        content="# 连点与压枪\n\n## 压枪\n压枪需要先开启。",
        group_id=group_id,
        author_id=1,
        category="06_连点与压枪",
    )

    accepted, rejected = await WikiScopeService().set_skills(group_id, ["qinex_recoil_click"], updated_by=1)
    recoil_hits = await WikiSearchService().search("压枪怎么开", group_id=group_id)
    mirror_hits = await WikiSearchService().search("投屏怎么开", group_id=group_id)

    assert accepted == ["06_连点与压枪"]
    assert rejected == []
    assert any(hit.article.article_no == faq.article_no and "连点" in hit.reference for hit in recoil_hits)
    assert not any(hit.article.article_no == faq.article_no for hit in mirror_hits)


@pytest.mark.asyncio
async def test_group_wiki_ask_no_result() -> None:
    await init_db()
    group_id = 840000000 + (uuid4().int % 100000000)

    response = await RAGService(Config(group_wiki_enable_ai=False)).ask(
        f"不存在的问题 {uuid4()}",
        group_id=group_id,
        user_id=1,
    )

    assert not response.references
    assert "暂时没有找到" in response.answer
