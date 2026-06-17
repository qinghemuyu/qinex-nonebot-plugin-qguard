from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_group_wiki.services.article_service import GroupWikiService
from nonebot_plugin_group_wiki.services.import_service import ImportService
from nonebot_plugin_group_wiki.services.rag_service import RAGService
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_group_wiki.services.skill_registry import describe_wiki_skills
from nonebot_plugin_group_wiki.services.scope_service import WikiScopeService
from nonebot_plugin_group_wiki.utils.formatter import (
    format_article,
    format_ask_response,
    format_import_result,
    format_search_results,
)

from ._common import finish_reply, get_event_group_id, is_admin_event, parse_wiki_command

wiki_matcher = on_message(priority=5, block=False)

HELP_TEXT = """GroupWiki 命令
/知识 导入本地
/知识 添加 标题 内容
/知识 搜索 关键词
/知识 分类
/知识 范围
/知识 范围 全部
/知识 范围 分类 分类1,分类2
/知识 范围 技能 qinex_recoil_click,qinex_screenhub
/知识 技能
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

    if action == "分类":
        categories = await WikiScopeService().list_categories(group_id=group_id)
        if not categories:
            await finish_reply(wiki_matcher, bot, event, "知识库还没有分类。先执行 /知识 导入本地。")
        await finish_reply(wiki_matcher, bot, event, "当前知识分类：\n" + "\n".join(f"- {item}" for item in categories))

    if action == "范围":
        await _handle_scope(bot, event, group_id, args_text)

    if action == "技能":
        await _handle_skills(bot, event, group_id, args_text)

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


async def _handle_scope(bot: Bot, event: MessageEvent, group_id: int | None, args_text: str) -> None:
    if group_id is None:
        await finish_reply(wiki_matcher, bot, event, "知识库范围只能在群里设置。")
    service = WikiScopeService()
    args = args_text.strip()
    if not args:
        allowed, all_categories = await service.get_group_scope(group_id)
        lines = ["本群知识库回答范围："]
        if allowed:
            lines.append("仅允许以下分类：")
            lines.extend(f"- {item}" for item in allowed)
        else:
            lines.append("全部分类")
        if all_categories:
            lines.append("")
            lines.append("可选分类：")
            lines.extend(f"- {item}" for item in all_categories)
        await finish_reply(wiki_matcher, bot, event, "\n".join(lines))

    if not is_admin_event(event):
        await finish_reply(wiki_matcher, bot, event, "只有群管理员可以修改知识库回答范围。")

    if args in {"全部", "全量", "all"}:
        await service.set_all(group_id, updated_by=event.user_id)
        await finish_reply(wiki_matcher, bot, event, "本群知识库回答范围已切换为：全部分类。")

    if args.startswith("分类 "):
        raw_categories = args.removeprefix("分类 ").strip()
        categories = [item.strip() for item in raw_categories.replace("，", ",").split(",") if item.strip()]
        if not categories:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 范围 分类 分类1,分类2")
        accepted, rejected = await service.set_categories(group_id, categories, updated_by=event.user_id)
        lines = ["本群知识库回答范围已更新。"]
        lines.append("生效分类：" + ("、".join(accepted) if accepted else "无"))
        if rejected:
            lines.append("未找到分类：" + "、".join(rejected))
        await finish_reply(wiki_matcher, bot, event, "\n".join(lines))

    if args.startswith("技能 "):
        raw_skills = args.removeprefix("技能 ").strip()
        skill_ids = [item.strip() for item in raw_skills.replace("，", ",").split(",") if item.strip()]
        if not skill_ids:
            await finish_reply(wiki_matcher, bot, event, "用法：/知识 范围 技能 qinex_recoil_click,qinex_screenhub")
        accepted, rejected = await service.set_skills(group_id, skill_ids, updated_by=event.user_id)
        lines = ["本群知识库回答范围已按 skill 更新。"]
        lines.append("生效分类：" + ("、".join(accepted) if accepted else "无"))
        if rejected:
            lines.append("未找到 skill/分类：" + "、".join(rejected))
        await finish_reply(wiki_matcher, bot, event, "\n".join(lines))

    await finish_reply(wiki_matcher, bot, event, "用法：/知识 范围、/知识 范围 全部、/知识 范围 分类 分类1,分类2、/知识 范围 技能 skill_id")


async def _handle_skills(bot: Bot, event: MessageEvent, group_id: int | None, args_text: str) -> None:
    if args_text.strip():
        await _handle_scope(bot, event, group_id, f"技能 {args_text.strip()}")
    service = WikiScopeService()
    allowed, _all_categories = await service.get_group_scope(group_id)
    lines = [describe_wiki_skills(), "", "本群当前范围：" + ("、".join(allowed) if allowed else "全部分类")]
    await finish_reply(wiki_matcher, bot, event, "\n".join(lines))
