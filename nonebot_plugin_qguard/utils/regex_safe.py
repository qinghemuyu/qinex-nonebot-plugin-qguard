import re


def safe_compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)
