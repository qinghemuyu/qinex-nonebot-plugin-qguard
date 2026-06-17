from dataclasses import dataclass
from uuid import uuid4

import pytest

from nonebot_plugin_group_wiki.commands._common import parse_wiki_command
from nonebot_plugin_group_wiki.commands.root import parse_title_content
from nonebot_plugin_group_wiki.config import Config
from nonebot_plugin_group_wiki.models import init_db
from nonebot_plugin_group_wiki.services.article_service import GroupWikiService
from nonebot_plugin_group_wiki.services.import_service import ImportService
from nonebot_plugin_group_wiki.services.rag_service import RAGService
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_group_wiki.utils.markdown import title_from_markdown
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


@dataclass
class FakeAICore:
    calls: int = 0

    async def chat(self, messages: list[dict], **kwargs) -> str:
        self.calls += 1
        assert "知识库片段" in messages[-1]["content"]
        return "根据知识库，先检查保存配置和输出模式。"


def test_parse_wiki_command() -> None:
    assert parse_wiki_command("/知识 搜索 压枪") == ("/知识", ["搜索"], "压枪")
    assert parse_wiki_command("/问 怎么压枪") == ("/问", [], "怎么压枪")
    assert parse_wiki_command("/管 状态") is None


def test_parse_title_content() -> None:
    assert parse_title_content("标题 内容 abc") == ("标题", "内容 abc")
    assert parse_title_content("only") == ("", "")


def test_markdown_helpers_and_splitter() -> None:
    assert title_from_markdown("# 标题\n正文", "fallback") == "标题"
    assert split_text("abcdef", chunk_size=3, overlap=1) == ["abc", "cde", "ef"]


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
    assert "知识库" in response.answer
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
