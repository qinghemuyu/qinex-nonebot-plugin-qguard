from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_group_wiki.services.article_service import GroupWikiService
from nonebot_plugin_group_wiki.services.import_service import ImportService
from nonebot_plugin_group_wiki.services.rag_service import RAGService
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_group_wiki.utils.formatter import (
    format_article,
    format_ask_response,
    format_import_result,
    format_search_results,
)

from ._common import finish_reply, get_event_group_id, parse_wiki_command

wiki_matcher = on_message(priority=5, block=False)

HELP_TEXT = """GroupWiki 命令
/知识 导入本地
/知识 添加 标题 内容
/知识 搜索 关键词
/知识 查看 K0001
/知识 有用 K0001
/知识 没用 K0001
/问 问题
/FAQ 关键词
"""


@wiki_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    parsed = parse_wiki_command(event.get_plaintext())
    if parsed is None:
        return
    command, actions, args_text = parsed
    group_id = get_event_group_id(event)

    if command in {"/问", "/FAQ", "/wiki", "/教程"}:
        if not args_text:
            await finish_reply(wiki_matcher, bot, event, "用法：/问 问题")
        response = await RAGService().ask(args_text, group_id=group_id, user_id=event.user_id)
        await finish_reply(wiki_matcher, bot, event, format_ask_response(response))

    action = actions[0] if actions else "帮助"
    if action in {"帮助", "help"}:
        await finish_reply(wiki_matcher, bot, event, HELP_TEXT)

    if action == "导入本地":
        created, updated, skipped = await ImportService().import_local_markdown(author_id=event.user_id)
        await finish_reply(wiki_matcher, bot, event, format_import_result(created, updated, skipped))

    if action == "添加":
        title, content = parse_title_content(args_text)
        if not title or not content:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 添加 标题 内容")
        article = await GroupWikiService().add_article(
            title=title,
            content=content,
            group_id=group_id,
            author_id=event.user_id,
        )
        await finish_reply(wiki_matcher, bot, event, f"知识已添加：[{article.article_no}] {article.title}")

    if action == "搜索":
        if not args_text:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 搜索 关键词")
        hits = await WikiSearchService().search(args_text, group_id=group_id, limit=5)
        await finish_reply(wiki_matcher, bot, event, format_search_results(hits))

    if action == "问":
        if not args_text:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 问 问题")
        response = await RAGService().ask(args_text, group_id=group_id, user_id=event.user_id)
        await finish_reply(wiki_matcher, bot, event, format_ask_response(response))

    if action == "查看":
        article_no = args_text.strip().upper()
        if not article_no:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 查看 K0001")
        article = await GroupWikiService().get_article(article_no)
        if article is None:
            await finish_reply(wiki_matcher, bot, event, "没有找到这篇知识。")
        await finish_reply(wiki_matcher, bot, event, format_article(article))

    if action in {"有用", "没用"}:
        article_no = args_text.strip().upper()
        if not article_no:
            await finish_reply(wiki_matcher, bot, event, f"用法：/知识 {action} K0001")
        feedback_type = "useful" if action == "有用" else "useless"
        ok = await GroupWikiService().feedback(
            article_no,
            feedback_type=feedback_type,
            group_id=group_id,
            user_id=event.user_id,
        )
        await finish_reply(wiki_matcher, bot, event, "已记录反馈。" if ok else "没有找到这篇知识。")


def parse_title_content(text: str) -> tuple[str, str]:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "", ""
    return parts[0], parts[1]
