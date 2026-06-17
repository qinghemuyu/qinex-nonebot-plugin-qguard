from .mask import mask_text

MAX_TEXT_CHARS = 12000


def clip_text(text: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars]}\n\n[已截断 {omitted} 字]"


def sanitize_messages(messages: list[dict], *, enable_mask: bool = True, max_chars: int = MAX_TEXT_CHARS) -> list[dict]:
    sanitized: list[dict] = []
    for message in messages:
        item = dict(message)
        content = item.get("content")
        if isinstance(content, str):
            content = clip_text(content, max_chars=max_chars)
            if enable_mask:
                content = mask_text(content)
            item["content"] = content
        sanitized.append(item)
    return sanitized
