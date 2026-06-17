import re

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def compact_duplicate_lines(text: str) -> str:
    result: list[str] = []
    previous = object()
    repeat_count = 0
    for line in text.splitlines():
        if line == previous:
            repeat_count += 1
            continue
        if repeat_count:
            result.append(f"[上一行重复 {repeat_count} 次]")
            repeat_count = 0
        result.append(line)
        previous = line
    if repeat_count:
        result.append(f"[上一行重复 {repeat_count} 次]")
    return "\n".join(result)
