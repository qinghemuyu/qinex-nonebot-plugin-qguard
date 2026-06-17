from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.index_repo import WikiSearchIndexRepo
from nonebot_plugin_group_wiki.repositories.scope_config_repo import WikiScopeConfigRepo
from nonebot_plugin_group_wiki.services.skill_registry import (
    FAQ_CATEGORY,
    faq_chunk_allowed_for_categories,
    find_skill,
    match_skill_id,
)
from nonebot_plugin_group_wiki.utils.rerank import SearchHit, score_article


class WikiSearchService:
    async def search(self, query: str, *, group_id: int | None = None, limit: int = 5) -> list[SearchHit]:
        if not query.strip():
            return []
        async with get_session() as session:
            article_repo = WikiArticleRepo(session)
            index_repo = WikiSearchIndexRepo(session)
            articles = await article_repo.list_published(group_id=group_id)
            allowed_categories = await WikiScopeConfigRepo(session).allowed_categories(group_id)
            hits: list[SearchHit] = []
            query_skill = find_skill(match_skill_id(query))
            for article in articles:
                chunks = await index_repo.chunks_by_article(article.id)
                if allowed_categories:
                    allowed = set(allowed_categories)
                    if article.category == FAQ_CATEGORY:
                        if query_skill is not None and not allowed.intersection(query_skill.primary_categories):
                            continue
                        chunks = [chunk for chunk in chunks if faq_chunk_allowed_for_categories(chunk, allowed_categories)]
                        if not chunks:
                            continue
                    elif article.category not in allowed:
                        continue
                hit = score_article(query, article, chunks)
                if hit is not None:
                    hits.append(hit)
            hits.sort(key=lambda item: item.score, reverse=True)
            for hit in hits[:limit]:
                await article_repo.increment_hit(hit.article)
            await session.commit()
            return hits[:limit]
