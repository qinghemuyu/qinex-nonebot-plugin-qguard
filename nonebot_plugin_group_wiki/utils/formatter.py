from nonebot_plugin_group_wiki.models import WikiArticle
from nonebot_plugin_group_wiki.services.schemas import AskResponse
from nonebot_plugin_group_wiki.utils.rerank import SearchHit


def format_search_results(hits: list[SearchHit]) -> str:
    if not hits:
        return "知识库没有找到相关内容。"
    lines = [f"找到 {len(hits)} 条相关知识："]
    for index, hit in enumerate(hits, start=1):
        lines.append(f"{index}. [{hit.article.article_no}] {hit.article.title}")
    return "\n".join(lines)


def format_article(article: WikiArticle) -> str:
    content = article.content_md.strip()
    if len(content) > 1000:
        content = content[:980] + "\n..."
    return f"[{article.article_no}] {article.title}\n分类：{article.category or '未分类'}\n\n{content}"


def format_ask_response(response: AskResponse) -> str:
    refs = "、".join(response.references) if response.references else "无"
    return f"{response.answer.strip()}\n\n参考：{refs}"


def format_import_result(created: int, updated: int, skipped: int) -> str:
    return f"知识库导入完成：新增 {created}，更新 {updated}，跳过 {skipped}。"
