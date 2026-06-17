from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_group_wiki.models import WikiSearchIndex


class WikiSearchIndexRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_chunks(self, article_id: int, chunks: list[tuple[int, str, str]]) -> None:
        await self.session.execute(delete(WikiSearchIndex).where(WikiSearchIndex.article_id == article_id))
        for chunk_id, chunk_text, chunk_hash in chunks:
            self.session.add(
                WikiSearchIndex(article_id=article_id, chunk_id=chunk_id, chunk_text=chunk_text, chunk_hash=chunk_hash)
            )
        await self.session.flush()

    async def chunks_by_article(self, article_id: int) -> list[str]:
        result = await self.session.scalars(
            select(WikiSearchIndex)
            .where(WikiSearchIndex.article_id == article_id)
            .order_by(WikiSearchIndex.chunk_id.asc())
        )
        return [item.chunk_text for item in result]
