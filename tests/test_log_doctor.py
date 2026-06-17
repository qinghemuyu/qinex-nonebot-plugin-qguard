import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest

from nonebot_plugin_log_doctor.commands._common import parse_log_doctor_command
from nonebot_plugin_log_doctor.config import Config
from nonebot_plugin_log_doctor.models import init_db
from nonebot_plugin_log_doctor.services.diagnose_service import LogDoctorService
from nonebot_plugin_log_doctor.services.formatter import format_diagnosis
from nonebot_plugin_log_doctor.services.preprocess_service import PreprocessService
from nonebot_plugin_log_doctor.services.rule_engine import RuleEngine
from nonebot_plugin_log_doctor.services.schemas import DiagnosisResult
from nonebot_plugin_log_doctor.utils.log_cleaner import strip_ansi


@dataclass
class FakeAIService:
    calls: int = 0

    async def diagnose(self, text: str, *, group_id: int | None = None, user_id: int | None = None) -> DiagnosisResult:
        self.calls += 1
        return DiagnosisResult(
            title="AI 识别错误",
            category="ai",
            severity="medium",
            confidence=0.77,
            root_cause="AI fallback",
            evidence=["fallback"],
            fix_steps=["检查日志"],
        )


def test_parse_log_doctor_command() -> None:
    assert parse_log_doctor_command("/诊断 abc") is None
    assert parse_log_doctor_command("/报错 xxx") is None
    assert parse_log_doctor_command("/logdoctor") is None
    assert parse_log_doctor_command("/管 状态") is None


def test_strip_ansi_and_preprocess_traceback() -> None:
    text = "\x1b[31mred\x1b[0m\nline\nTraceback (most recent call last):\nModuleNotFoundError: No module named 'x'"
    assert strip_ansi(text).startswith("red")
    cleaned = PreprocessService(Config(log_doctor_max_input_chars=200)).preprocess(text)
    assert cleaned.startswith("Traceback")
    assert "ModuleNotFoundError" in cleaned


def test_rule_engine_sqlite() -> None:
    result = RuleEngine().match("sqlite3.OperationalError: unable to open database file")

    assert result is not None
    assert result.category == "database_path_or_permission"
    assert result.confidence >= 0.9


def test_rule_engine_does_not_treat_successful_onebot_connection_as_error() -> None:
    result = RuleEngine().match("OneBot V11 | Bot 3195276161 connected")

    assert result is None


@pytest.mark.asyncio
async def test_log_doctor_rule_diagnosis_records() -> None:
    await init_db()
    service = LogDoctorService(config=Config(log_doctor_enable_ai=False))
    group_id = 820000000 + (uuid4().int % 100000000)

    response = await service.diagnose_text(
        "ModuleNotFoundError: No module named 'nonebot_plugin_demo'",
        group_id=group_id,
        user_id=123,
    )
    records = await service.latest_records(group_id=group_id, limit=1)

    assert not response.ai_used
    assert response.record_no.startswith("D")
    assert response.result.category == "missing_dependency"
    assert records[0].record_no == response.record_no


@pytest.mark.asyncio
async def test_log_doctor_ai_fallback() -> None:
    await init_db()
    ai_service = FakeAIService()
    service = LogDoctorService(config=Config(log_doctor_enable_ai=True), ai_service=ai_service)

    response = await service.diagnose_text("some unknown weird log", group_id=1, user_id=2)

    assert response.ai_used
    assert ai_service.calls == 1
    assert response.result.title == "AI 识别错误"


def test_format_diagnosis_limits_length() -> None:
    result = DiagnosisResult(
        title="测试",
        category="demo",
        severity="low",
        confidence=0.5,
        root_cause="x" * 500,
        fix_steps=["a" * 500],
    )
    response = type("Resp", (), {"result": result, "record_no": "D1", "ai_used": False})()

    text = format_diagnosis(response, Config(log_doctor_max_reply_chars=300))

    assert len(text) <= 320


def test_init_db_is_reentrant() -> None:
    asyncio.run(init_db())
