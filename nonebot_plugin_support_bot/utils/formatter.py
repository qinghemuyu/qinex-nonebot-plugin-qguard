from nonebot_plugin_support_bot.services.schemas import SupportIntent


def trim_reply(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 12)].rstrip() + "\n..."


def format_followup(intent: SupportIntent) -> str:
    fields = (intent.missing_fields or ["你用的是哪个功能", "卡在哪一步"])[:2]
    prefix = "喵，这个信息还不够，我先不乱猜。"
    if len(fields) == 1:
        return f"{prefix}先告诉我{fields[0]}，我再给你下一步。"
    return f"{prefix}简单说下：{fields[0]}；还有{fields[1]}。"
