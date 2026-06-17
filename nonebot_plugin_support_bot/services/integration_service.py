from typing import Any


def _require_plugin(plugin_name: str) -> None:
    from nonebot import require

    require(plugin_name)


class IntegrationService:
    async def ask_wiki(
        self,
        question: str,
        *,
        group_id: int | None,
        user_id: int | None,
        search_query: str | None = None,
    ) -> Any:
        try:
            from nonebot_plugin_group_wiki.services.rag_service import RAGService
        except ModuleNotFoundError as exc:
            if exc.name and not exc.name.startswith("nonebot_plugin_group_wiki"):
                raise
            _require_plugin("nonebot_plugin_group_wiki")
            from nonebot_plugin_group_wiki.services.rag_service import RAGService
        return await RAGService().ask(question, group_id=group_id, user_id=user_id, search_query=search_query)
