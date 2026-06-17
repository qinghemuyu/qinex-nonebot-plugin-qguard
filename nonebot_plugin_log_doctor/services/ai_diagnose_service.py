from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot_plugin_ai_core.service import AICoreService

from nonebot_plugin_log_doctor.services.schemas import DiagnosisResult


def _get_ai_core() -> AICoreService:
    try:
        from nonebot_plugin_ai_core.service import get_ai_core
    except ModuleNotFoundError as exc:
        if exc.name and not exc.name.startswith("nonebot_plugin_ai_core"):
            raise
        from nonebot import require

        require("nonebot_plugin_ai_core")
        from nonebot_plugin_ai_core.service import get_ai_core
    return get_ai_core()


class AIDiagnoseService:
    def __init__(self, ai_core: AICoreService | None = None) -> None:
        self.ai_core = ai_core

    async def diagnose(self, text: str, *, group_id: int | None = None, user_id: int | None = None) -> DiagnosisResult:
        ai_core = self.ai_core or _get_ai_core()
        result = await ai_core.extract_json(
            [
                {
                    "role": "system",
                    "content": (
                        "你是资深 Python / NoneBot / OneBot / Linux / SQLite / SQLAlchemy 故障诊断专家。"
                        "请根据日志给出可执行、保守的诊断。不要编造不存在的信息。"
                    ),
                },
                {"role": "user", "content": text},
            ],
            DiagnosisResult,
            user_id=user_id,
            group_id=group_id,
            purpose="log_doctor_diagnose",
        )
        return result
