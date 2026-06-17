import re

MASKED = "[已脱敏]"

PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{6,}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)[1-9]\d{4,11}(?!\d)"),
)


def mask_text(text: str) -> str:
    masked = text
    for pattern in PATTERNS:
        masked = pattern.sub(MASKED, masked)
    return masked
