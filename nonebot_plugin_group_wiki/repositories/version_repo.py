from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_group_wiki.models import WikiArticle, WikiArticleVersion


class WikiArticleVersionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(self, article: WikiArticle, editor_id: int | None, change_note: str) -> WikiArticleVersion:
        version = WikiArticleVersion(
            article_id=article.id,
            version=article.version,
            content_md=article.content_md,
            summary=article.summary,
            editor_id=editor_id,
            change_note=change_note,
        )
        self.session.add(version)
        await self.session.flush()
        return version
