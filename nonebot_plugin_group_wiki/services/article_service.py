from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.models import WikiArticle, get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.feedback_repo import WikiFeedbackRepo
from nonebot_plugin_group_wiki.repositories.index_repo import WikiSearchIndexRepo
from nonebot_plugin_group_wiki.repositories.version_repo import WikiArticleVersionRepo
from nonebot_plugin_group_wiki.services.chunk_service import ChunkService


class GroupWikiService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self.chunk_service = ChunkService(self.config)

    async def add_article(
        self,
        *,
        title: str,
        content: str,
        group_id: int | None,
        author_id: int | None,
        scope: str | None = None,
        source_type: str = "manual",
        source_ref_id: str = "",
        category: str = "",
        summary: str = "",
    ) -> WikiArticle:
        content = content.strip()[: self.config.group_wiki_max_article_length]
        scope = scope or self.config.group_wiki_default_scope
        article_group_id = 0 if scope == "global" else int(group_id or 0)
        async with get_session() as session:
            article_repo = WikiArticleRepo(session)
            article = await article_repo.create(
                WikiArticle(
                    group_id=article_group_id,
                    scope=scope,
                    title=title.strip(),
                    summary=summary.strip(),
                    content_md=content,
                    status="published",
                    category=category,
                    author_id=author_id,
                    source_type=source_type,
                    source_ref_id=source_ref_id,
                )
            )
            await WikiArticleVersionRepo(session).create_snapshot(article, author_id, "create")
            await WikiSearchIndexRepo(session).replace_chunks(
                article.id,
                self.chunk_service.build_chunks(article.title, article.summary, article.content_md),
            )
            await session.commit()
            return article

    async def get_article(self, article_no: str) -> WikiArticle | None:
        async with get_session() as session:
            article = await WikiArticleRepo(session).get_by_no(article_no)
            if article is not None:
                article.view_count += 1
                await session.commit()
            return article

    async def feedback(
        self,
        article_no: str,
        *,
        feedback_type: str,
        group_id: int | None,
        user_id: int | None,
    ) -> bool:
        async with get_session() as session:
            article = await WikiArticleRepo(session).get_by_no(article_no)
            if article is None:
                return False
            await WikiFeedbackRepo(session).create(
                article,
                group_id=group_id,
                user_id=user_id,
                feedback_type=feedback_type,
            )
            await session.commit()
            return True
