import re

from nonebot_plugin_qguard.constants import PERMANENT_MUTE_SECONDS

_TIME_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd秒分时天]?)$")


def parse_duration(text: str, permanent_seconds: int = PERMANENT_MUTE_SECONDS) -> int:
    value = text.strip().lower()
    if value in {"永久", "永远", "forever"}:
        return permanent_seconds
    if value == "0":
        return 0
    match = _TIME_RE.match(value)
    if not match:
        raise ValueError(f"无法解析时间：{text}")
    number = int(match.group("value"))
    unit = match.group("unit") or "s"
    multipliers = {
        "s": 1,
        "秒": 1,
        "m": 60,
        "分": 60,
        "h": 3600,
        "时": 3600,
        "d": 86400,
        "天": 86400,
    }
    return number * multipliers[unit]
