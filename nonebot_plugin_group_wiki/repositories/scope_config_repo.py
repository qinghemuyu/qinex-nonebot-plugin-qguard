import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_group_wiki.models import WikiGroupScopeConfig


class WikiScopeConfigRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, group_id: int) -> WikiGroupScopeConfig:
        result = await self.session.scalars(
            select(WikiGroupScopeConfig).where(WikiGroupScopeConfig.group_id == group_id)
        )
        item = result.one_or_none()
        if item is not None:
            return item
        item = WikiGroupScopeConfig(group_id=group_id)
        self.session.add(item)
        await self.session.flush()
        return item

    async def allowed_categories(self, group_id: int | None) -> list[str]:
        if group_id is None:
            return []
        item = await self.get_or_create(group_id)
        try:
            parsed = json.loads(item.allowed_categories_json or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(category).strip() for category in parsed if str(category).strip()]

    async def set_allowed_categories(
        self,
        group_id: int,
        categories: list[str],
        *,
        updated_by: int | None = None,
    ) -> WikiGroupScopeConfig:
        item = await self.get_or_create(group_id)
        normalized = _normalize_categories(categories)
        item.allowed_categories_json = json.dumps(normalized, ensure_ascii=False)
        item.updated_by = updated_by
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item


def _normalize_categories(categories: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for category in categories:
        name = category.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result
