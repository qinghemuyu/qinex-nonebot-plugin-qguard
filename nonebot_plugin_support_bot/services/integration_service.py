from typing import Any


def _require_plugin(plugin_name: str) -> None:
    from nonebot import require

    require(plugin_name)


class IntegrationService:
    async def ask_wiki(self, question: str, *, group_id: int | None, user_id: int | None) -> Any:
        try:
            from nonebot_plugin_group_wiki.services.rag_service import RAGService
        except ModuleNotFoundError as exc:
            if exc.name and not exc.name.startswith("nonebot_plugin_group_wiki"):
                raise
            _require_plugin("nonebot_plugin_group_wiki")
            from nonebot_plugin_group_wiki.services.rag_service import RAGService
        return await RAGService().ask(question, group_id=group_id, user_id=user_id)

    async def diagnose_log(self, text: str, *, group_id: int | None, user_id: int | None) -> Any:
        try:
            from nonebot_plugin_log_doctor.services.diagnose_service import LogDoctorService
        except ModuleNotFoundError as exc:
            if exc.name and not exc.name.startswith("nonebot_plugin_log_doctor"):
                raise
            _require_plugin("nonebot_plugin_log_doctor")
            from nonebot_plugin_log_doctor.services.diagnose_service import LogDoctorService
        return await LogDoctorService().diagnose_text(
            text,
            group_id=group_id,
            user_id=user_id,
            source_type="support_bot",
        )
