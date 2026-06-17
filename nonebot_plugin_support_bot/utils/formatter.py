from nonebot_plugin_support_bot.services.schemas import SupportIntent


def trim_reply(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 12)].rstrip() + "\n..."


def format_followup(intent: SupportIntent) -> str:
    fields = (intent.missing_fields or ["使用的是哪个功能", "卡在哪一步", "当前看到的现象"])[:3]
    prefixes = ("一、", "二、", "三、")
    lines = ["喵，我先按 QInEX 问题帮你判断。为了更准一点，补充这几项就行："]
    for index, field in enumerate(fields):
        lines.append(f"{prefixes[index]}{field}")
    return "\n".join(lines)
