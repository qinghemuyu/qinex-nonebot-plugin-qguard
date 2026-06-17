import json
from typing import Any

from nonebot_plugin_support_bot.models import Ticket, TicketMessage
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
    lines.append("也可以直接发 /人工，我会创建工单给管理员处理。")
    return "\n".join(lines)


def format_ticket_created(ticket: Ticket) -> str:
    return (
        f"已创建工单 {ticket.ticket_no}\n"
        f"状态：{ticket.status}\n"
        f"类型：{ticket.issue_type}\n"
        f"摘要：{ticket.summary}\n"
        "管理员可以用 /工单 接单、/工单 备注、/工单 关闭 处理。"
    )


def format_ticket(ticket: Ticket, messages: list[TicketMessage] | None = None) -> str:
    refs = ""
    try:
        wiki_ids = json.loads(ticket.related_wiki_ids_json or "[]")
        refs = "、".join(wiki_ids)
    except json.JSONDecodeError:
        refs = ""
    lines = [
        f"工单 {ticket.ticket_no}",
        f"状态：{ticket.status}",
        f"优先级：{ticket.priority}",
        f"类型：{ticket.issue_type}",
        f"提交人：{ticket.user_id}",
        f"接单人：{ticket.assignee_id or '未接单'}",
        f"摘要：{ticket.summary}",
    ]
    if ticket.related_diagnosis_id:
        lines.append(f"诊断：{ticket.related_diagnosis_id}")
    if refs:
        lines.append(f"知识引用：{refs}")
    if messages:
        lines.append("最近记录：")
        for item in messages[-5:]:
            lines.append(f"- {item.sender_role}: {item.content[:80]}")
    return "\n".join(lines)


def format_ticket_list(tickets: list[Ticket]) -> str:
    if not tickets:
        return "暂无工单。"
    lines = [f"共 {len(tickets)} 条工单："]
    for ticket in tickets:
        lines.append(f"- {ticket.ticket_no} [{ticket.status}] {ticket.summary}")
    return "\n".join(lines)


def format_diagnosis_reply(diagnosis: Any, *, wiki_answer: str = "", references: list[str] | None = None) -> str:
    result = getattr(diagnosis, "result", None)
    record_no = getattr(diagnosis, "record_no", "")
    if result is None:
        return "诊断完成，但没有拿到结构化结果。可以补充完整日志或发 /人工。"
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
    lines.append("如果照做后还是不行，发 /人工 或 /工单 创建 <问题>。")
    return "\n".join(lines)
