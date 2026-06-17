from typing import Any

from nonebot_plugin_support_bot.services.schemas import SupportIntent


def trim_reply(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 12)].rstrip() + "\n..."


def format_followup(intent: SupportIntent) -> str:
    fields = intent.missing_fields or ["软件版本", "系统版本", "具体现象", "截图或日志"]
    lines = ["我先接住这个问题。为了判断得准一点，请补充："]
    for index, field in enumerate(fields, start=1):
        lines.append(f"{index}. {field}：")
    lines.append("如果是完整日志或 Traceback，请使用 /诊断 或 /报错。")
    return "\n".join(lines)


def format_diagnosis_reply(diagnosis: Any, *, wiki_answer: str = "", references: list[str] | None = None) -> str:
    result = getattr(diagnosis, "result", None)
    record_no = getattr(diagnosis, "record_no", "")
    if result is None:
        return "诊断完成，但没有拿到结构化结果。可以补充完整日志后再试。"
    steps = list(getattr(result, "fix_steps", []) or [])
    questions = list(getattr(result, "questions", []) or [])
    lines = [
        f"诊断 {record_no}",
        f"结论：{getattr(result, 'title', '未知问题')}",
        f"原因：{getattr(result, 'root_cause', '暂未明确')}",
    ]
    if steps:
        lines.append("建议：")
        for index, step in enumerate(steps[:4], start=1):
            lines.append(f"{index}. {step}")
    if wiki_answer and references:
        lines.append("")
        lines.append("相关知识库：")
        lines.append(wiki_answer)
        lines.append(f"参考：{'、'.join(references)}")
    if questions:
        lines.append("")
        lines.append("还需要补充：")
        for question in questions[:3]:
            lines.append(f"- {question}")
    lines.append("如果照做后还是不行，请补充新的现象、日志或截图。")
    return "\n".join(lines)
