from datetime import datetime

from sqlalchemy import distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_group_wiki.models import WikiArticle


class WikiArticleRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, article: WikiArticle) -> WikiArticle:
        self.session.add(article)
        await self.session.flush()
        article.article_no = f"K{article.id:04d}"
        await self.session.flush()
        return article

    async def get_by_no(self, article_no: str) -> WikiArticle | None:
        result = await self.session.scalars(
            select(WikiArticle).where(WikiArticle.article_no == article_no.upper())
        )
        return result.one_or_none()

    async def get_by_source(self, source_type: str, source_ref_id: str) -> WikiArticle | None:
        result = await self.session.scalars(
            select(WikiArticle).where(
                WikiArticle.source_type == source_type,
                WikiArticle.source_ref_id == source_ref_id,
            )
        )
        return result.one_or_none()

    async def upsert_imported(
        self,
        *,
        source_ref_id: str,
        title: str,
        summary: str,
        content_md: str,
        category: str,
        author_id: int | None,
    ) -> tuple[WikiArticle, str]:
        existing = await self.get_by_source("import", source_ref_id)
        if existing is None:
            article = await self.create(
                WikiArticle(
                    group_id=0,
                    scope="global",
                    title=title,
                    summary=summary,
                    content_md=content_md,
                    status="published",
                    category=category,
                    author_id=author_id,
                    source_type="import",
                    source_ref_id=source_ref_id,
                    published_at=datetime.utcnow(),
                )
            )
            return article, "created"
        changed = (
            existing.title != title
            or existing.content_md != content_md
            or existing.summary != summary
            or existing.category != category
        )
        if not changed:
            return existing, "skipped"
        existing.title = title
        existing.summary = summary
        existing.content_md = content_md
        existing.category = category
        existing.version += 1
        existing.updated_at = datetime.utcnow()
        await self.session.flush()
        return existing, "updated"

    async def list_published(self, group_id: int | None = None) -> list[WikiArticle]:
        clauses = [WikiArticle.status == "published"]
        if group_id is not None:
            clauses.append(or_(WikiArticle.group_id == 0, WikiArticle.group_id == group_id))
        result = await self.session.scalars(select(WikiArticle).where(*clauses).order_by(WikiArticle.id.desc()))
        return list(result)

    async def list_categories(self, group_id: int | None = None) -> list[str]:
        clauses = [WikiArticle.status == "published"]
        if group_id is not None:
            clauses.append(or_(WikiArticle.group_id == 0, WikiArticle.group_id == group_id))
        result = await self.session.scalars(
            select(distinct(WikiArticle.category)).where(*clauses).order_by(WikiArticle.category.asc())
        )
        return [item for item in result if item]

    async def increment_hit(self, article: WikiArticle) -> None:
        article.hit_count += 1
        await self.session.flush()
