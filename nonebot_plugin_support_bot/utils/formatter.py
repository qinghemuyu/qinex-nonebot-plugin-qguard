from nonebot_plugin_support_bot.services.schemas import SupportIntent


def trim_reply(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 12)].rstrip() + "\n..."


def format_followup(intent: SupportIntent) -> str:
    fields = (intent.missing_fields or ["你用的是哪个功能", "卡在哪一步"])[:2]
    if len(fields) == 1:
        return f"喵，我大概懂啦～先告诉我{fields[0]}，我好给你对症的步骤。"
    return f"喵，想帮你更准一点，简单说下{fields[0]}？再说下{fields[1]}就行。"
