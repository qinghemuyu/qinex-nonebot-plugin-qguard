import json

from nonebot_plugin_log_doctor.config import Config, load_config
from nonebot_plugin_log_doctor.models import DiagnosisRecord, get_session
from nonebot_plugin_log_doctor.repositories.diagnosis_repo import DiagnosisRecordRepo
from nonebot_plugin_log_doctor.services.ai_diagnose_service import AIDiagnoseService
from nonebot_plugin_log_doctor.services.preprocess_service import PreprocessService
from nonebot_plugin_log_doctor.services.rule_engine import RuleEngine
from nonebot_plugin_log_doctor.services.schemas import DiagnosisResponse, DiagnosisResult
from nonebot_plugin_log_doctor.utils.hash import hash_text


class LogDoctorService:
    def __init__(
        self,
        *,
        config: Config | None = None,
        rule_engine: RuleEngine | None = None,
        ai_service: AIDiagnoseService | None = None,
        preprocess_service: PreprocessService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.rule_engine = rule_engine or RuleEngine()
        self.ai_service = ai_service or AIDiagnoseService()
        self.preprocess_service = preprocess_service or PreprocessService(self.config)

    async def diagnose_text(
        self,
        text: str,
        *,
        group_id: int | None = None,
        user_id: int | None = None,
        source_type: str = "command",
    ) -> DiagnosisResponse:
        cleaned = self.preprocess_service.preprocess(text)
        result = self.rule_engine.match(cleaned)
        ai_used = False

        if result is None and self.config.log_doctor_enable_ai:
            try:
                result = await self.ai_service.diagnose(cleaned, group_id=group_id, user_id=user_id)
                ai_used = True
            except Exception as exc:
                result = self._ai_failed_result(exc)
                ai_used = True

        if result is None:
            result = self._unknown_result()

        record = await self._save_record(
            result,
            cleaned,
            group_id=group_id,
            user_id=user_id,
            source_type=source_type,
            ai_used=ai_used,
        )
        return DiagnosisResponse(result=result, record_no=record.record_no, ai_used=ai_used, source_type=source_type)

    async def latest_records(self, group_id: int | None = None, limit: int = 5) -> list[DiagnosisRecord]:
        async with get_session() as session:
            return await DiagnosisRecordRepo(session).latest(group_id=group_id, limit=limit)

    async def _save_record(
        self,
        result: DiagnosisResult,
        cleaned_text: str,
        *,
        group_id: int | None,
        user_id: int | None,
        source_type: str,
        ai_used: bool,
    ) -> DiagnosisRecord:
        async with get_session() as session:
            record = await DiagnosisRecordRepo(session).create(
                DiagnosisRecord(
                    group_id=group_id,
                    user_id=user_id,
                    source_type=source_type,
                    raw_text_hash=hash_text(cleaned_text),
                    raw_text_excerpt=cleaned_text[:1000],
                    category=result.category,
                    severity=result.severity,
                    confidence=result.confidence,
                    title=result.title,
                    root_cause=result.root_cause,
                    fix_steps_json=json.dumps(result.fix_steps, ensure_ascii=False),
                    questions_json=json.dumps(result.questions, ensure_ascii=False),
                    ai_used=ai_used,
                )
            )
            await session.commit()
            return record

    @staticmethod
    def _unknown_result() -> DiagnosisResult:
        return DiagnosisResult(
            title="暂未识别出明确错误",
            category="unknown",
            severity="medium",
            confidence=0.2,
            root_cause="当前日志没有命中内置规则，且 AI 诊断未启用。",
            evidence=[],
            fix_steps=["补充完整 Traceback、启动命令、运行环境和最近改动。"],
            need_more_info=True,
            questions=["请贴出完整 Traceback。", "请说明运行系统、Python 版本和启动方式。"],
        )

    @staticmethod
    def _ai_failed_result(exc: Exception) -> DiagnosisResult:
        return DiagnosisResult(
            title="AI 诊断暂时不可用",
            category="ai_unavailable",
            severity="medium",
            confidence=0.4,
            root_cause=f"内置规则未命中，调用 AI Core 时失败：{exc}",
            evidence=[],
            fix_steps=["检查 AI_CORE_API_KEY、AI_CORE_BASE_URL、AI_CORE_MODEL 是否正确。", "稍后重试或补充更完整日志。"],
            need_more_info=True,
            questions=["请补充完整日志或稍后再次诊断。"],
        )
