from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.scope_config_repo import WikiScopeConfigRepo


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
            known = set(all_categories)
            accepted = [category for category in categories if category in known]
            rejected = [category for category in categories if category not in known]
            await WikiScopeConfigRepo(session).set_allowed_categories(group_id, accepted, updated_by=updated_by)
            await session.commit()
            return accepted, rejected
