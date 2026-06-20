from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.ad_keyword import AdKeyword


class AdKeywordRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_enabled(self, group_id: int, limit: int = 1000) -> list[AdKeyword]:
        result = await self.session.scalars(
            select(AdKeyword)
            .where(AdKeyword.group_id == group_id, AdKeyword.enabled.is_(True))
            .order_by(AdKeyword.id.desc())
            .limit(limit)
        )
        return list(result)

    async def list_all(self, group_id: int, limit: int = 50, offset: int = 0) -> list[AdKeyword]:
        result = await self.session.scalars(
            select(AdKeyword)
            .where(AdKeyword.group_id == group_id)
            .order_by(AdKeyword.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result)

    async def count_all(self, group_id: int) -> int:
        result = await self.session.scalar(
            select(func.count()).select_from(AdKeyword).where(AdKeyword.group_id == group_id)
        )
        return int(result or 0)

    async def get(self, keyword_id: int) -> AdKeyword | None:
        return await self.session.get(AdKeyword, keyword_id)

    async def add(self, group_id: int, keyword: str, created_by: int) -> tuple[AdKeyword, bool]:
        normalized = keyword.casefold()
        for item in await self.list_all(group_id, limit=500):
            if item.keyword.casefold() == normalized:
                created = False
                item.keyword = keyword
                item.enabled = True
                item.created_by = created_by
                await self.session.flush()
                return item, created

        item = AdKeyword(group_id=group_id, keyword=keyword, created_by=created_by)
        self.session.add(item)
        await self.session.flush()
        return item, True

    async def add_missing(self, group_id: int, keywords: Iterable[str], created_by: int) -> int:
        normalized_keywords: dict[str, str] = {}
        for keyword in keywords:
            clean = keyword.strip()
            if clean:
                normalized_keywords.setdefault(clean.casefold(), clean)

        if not normalized_keywords:
            return 0

        existing_result = await self.session.scalars(select(AdKeyword).where(AdKeyword.group_id == group_id))
        existing = {item.keyword.casefold() for item in existing_result}
        created = 0
        for normalized, keyword in normalized_keywords.items():
            if normalized in existing:
                continue
            self.session.add(AdKeyword(group_id=group_id, keyword=keyword, created_by=created_by))
            existing.add(normalized)
            created += 1

        if created:
            await self.session.flush()
        return created

    async def disable(self, keyword_id: int, group_id: int) -> AdKeyword | None:
        item = await self.get(keyword_id)
        if item is None or item.group_id != group_id:
            return None
        item.enabled = False
        await self.session.flush()
        return item
