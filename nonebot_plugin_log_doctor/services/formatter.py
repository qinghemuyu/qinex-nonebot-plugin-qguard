import json

from nonebot_plugin_log_doctor.config import Config, load_config
from nonebot_plugin_log_doctor.models import DiagnosisRecord
from nonebot_plugin_log_doctor.rules.builtin import BuiltinRule
from nonebot_plugin_log_doctor.services.schemas import DiagnosisResponse, DiagnosisResult
from nonebot_plugin_log_doctor.utils.text_limit import limit_text


SEVERITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "严重",
}


def format_diagnosis(response: DiagnosisResponse, config: Config | None = None) -> str:
    config = config or load_config()
    result = response.result
    lines = [
        f"【日志诊断】{result.title}",
        "",
        f"原因：{result.root_cause}",
        f"置信度：{int(result.confidence * 100)}%",
        f"严重程度：{SEVERITY_LABELS.get(result.severity, result.severity)}",
        f"诊断ID：{response.record_no}",
    ]
    if result.fix_steps:
        lines.append("")
        lines.append("建议修复：")
        for index, step in enumerate(result.fix_steps[:6], start=1):
            lines.append(f"{index}. {step}")
    if result.commands:
        lines.append("")
        lines.append("可参考命令：")
        for command in result.commands[:4]:
            lines.append(command)
    if result.questions:
        lines.append("")
        lines.append("需要补充：")
        for question in result.questions[:4]:
            lines.append(f"- {question}")
    if response.ai_used:
        lines.append("")
        lines.append("来源：AI 诊断")
    else:
        lines.append("")
        lines.append("来源：内置规则")
    return limit_text("\n".join(lines), config.log_doctor_max_reply_chars)


def format_recent_records(records: list[DiagnosisRecord]) -> str:
    if not records:
        return "暂无诊断记录。"
    lines = ["最近诊断："]
    for item in records:
        lines.append(f"{item.record_no} {item.title}（{item.category}，{int(item.confidence * 100)}%）")
    return "\n".join(lines)


def format_rules(rules: list[BuiltinRule]) -> str:
    lines = ["内置诊断规则："]
    for rule in rules:
        lines.append(f"- {rule.name}：{rule.title}")
    return "\n".join(lines)


def decode_steps(record: DiagnosisRecord) -> list[str]:
    try:
        data = json.loads(record.fix_steps_json)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def decode_questions(record: DiagnosisRecord) -> list[str]:
    try:
        data = json.loads(record.questions_json)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []
