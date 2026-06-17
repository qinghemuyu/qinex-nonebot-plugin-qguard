from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.scope_config_repo import WikiScopeConfigRepo
from nonebot_plugin_group_wiki.services.skill_registry import categories_for_skill_ids


class WikiScopeService:
    async def list_categories(self, group_id: int | None = None) -> list[str]:
        async with get_session() as session:
            return await WikiArticleRepo(session).list_categories(group_id=group_id)

    async def get_group_scope(self, group_id: int | None) -> tuple[list[str], list[str]]:
        async with get_session() as session:
            all_categories = await WikiArticleRepo(session).list_categories(group_id=group_id)
            allowed = await WikiScopeConfigRepo(session).allowed_categories(group_id)
            return allowed, all_categories

    async def set_all(self, group_id: int, *, updated_by: int | None = None) -> None:
        async with get_session() as session:
            await WikiScopeConfigRepo(session).set_allowed_categories(group_id, [], updated_by=updated_by)
            await session.commit()

    async def set_categories(
        self,
        group_id: int,
        categories: list[str],
        *,
        updated_by: int | None = None,
    ) -> tuple[list[str], list[str]]:
        async with get_session() as session:
            all_categories = await WikiArticleRepo(session).list_categories(group_id=group_id)
            accepted, rejected = _resolve_categories(categories, all_categories)
            await WikiScopeConfigRepo(session).set_allowed_categories(group_id, accepted, updated_by=updated_by)
            await session.commit()
            return accepted, rejected

    async def set_skills(
        self,
        group_id: int,
        skill_ids: list[str],
        *,
        updated_by: int | None = None,
    ) -> tuple[list[str], list[str]]:
        categories, rejected_skills = categories_for_skill_ids(skill_ids)
        accepted, rejected_categories = await self.set_categories(group_id, categories, updated_by=updated_by)
        return accepted, [*rejected_skills, *rejected_categories]


def _resolve_categories(categories: list[str], all_categories: list[str]) -> tuple[list[str], list[str]]:
    known = set(all_categories)
    aliases = {_category_alias(category): category for category in all_categories}
    accepted: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for raw in categories:
        candidate = raw.strip()
        resolved = candidate if candidate in known else aliases.get(_category_alias(candidate), "")
        if resolved:
            if resolved not in seen:
                accepted.append(resolved)
                seen.add(resolved)
        elif candidate:
            rejected.append(candidate)
    return accepted, rejected


def _category_alias(category: str) -> str:
    text = category.strip()
    if "_" in text:
        text = text.split("_", 1)[-1]
    return text.lower()
