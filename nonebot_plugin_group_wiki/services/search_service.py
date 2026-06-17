from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.index_repo import WikiSearchIndexRepo
from nonebot_plugin_group_wiki.utils.rerank import SearchHit, score_article


class WikiSearchService:
    async def search(self, query: str, *, group_id: int | None = None, limit: int = 5) -> list[SearchHit]:
        if not query.strip():
            return []
        async with get_session() as session:
            article_repo = WikiArticleRepo(session)
            index_repo = WikiSearchIndexRepo(session)
            articles = await article_repo.list_published(group_id=group_id)
            hits: list[SearchHit] = []
            for article in articles:
                chunks = await index_repo.chunks_by_article(article.id)
                hit = score_article(query, article, chunks)
                if hit is not None:
                    hits.append(hit)
            hits.sort(key=lambda item: item.score, reverse=True)
            for hit in hits[:limit]:
                await article_repo.increment_hit(hit.article)
            await session.commit()
            return hits[:limit]
