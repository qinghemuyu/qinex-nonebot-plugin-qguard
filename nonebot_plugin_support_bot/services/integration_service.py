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

    async def casual_chat(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int | None,
        software_name: str,
        max_tokens: int,
    ) -> str:
        try:
            from nonebot_plugin_ai_core import get_ai_core
        except ModuleNotFoundError as exc:
            if exc.name and not exc.name.startswith("nonebot_plugin_ai_core"):
                raise
            _require_plugin("nonebot_plugin_ai_core")
            from nonebot_plugin_ai_core import get_ai_core

        return await get_ai_core().chat(
            [
                {
                    "role": "system",
                    "content": (
                        f"你是 QQ 群里的{software_name}猫娘助手，名字叫雪。"
                        "可以自然闲聊，语气轻松、有一点猫娘感，但不要油腻，不要长篇说教。"
                        f"如果用户问{software_name}、映射、S3、P4、上位机、投屏、激活等软件问题，"
                        "只做轻量回应并提醒他直接描述现象，我会按知识库排查。"
                        "不要编造产品功能、授权政策、价格、密钥、算法或内部实现。"
                        "不要输出 Markdown 表格，不要分很多条，控制在 1 到 3 句。"
                    ),
                },
                {"role": "user", "content": text.strip()[:800]},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
            user_id=user_id,
            group_id=group_id,
            purpose="support_casual_chat",
        )
