import re
from typing import Any

from nonebot_plugin_qguard.enums import RuleAction, RuleType


class AntiAdService:
    _invite_patterns = (
        re.compile(r"(?:加群|进群|群号|q群|qq群|裙号).{0,16}\d{5,}", re.IGNORECASE),
        re.compile(r"(?:微信|v信|vx|qq|企鹅)[:：\s]*[a-zA-Z0-9_-]{5,}", re.IGNORECASE),
    )
    _ad_keywords = {
        "加群",
        "进群",
        "群号",
        "qq群",
        "q群",
        "裙号",
        "私聊",
        "推广",
        "引流",
        "代理",
        "返利",
        "刷单",
        "兼职",
        "免费领",
        "免费领取",
        "低价",
        "代充",
        "下载",
    }

    def check(self, plain_text: str, link_count: int = 0, at_count: int = 0) -> dict[str, Any] | None:
        text = plain_text.strip()
        if not text and link_count <= 0:
            return None

        normalized = text.lower()
        score = 0
        reasons: list[str] = []

        if link_count > 0:
            score += 1
            reasons.append("包含链接")
        if any(keyword in normalized for keyword in self._ad_keywords):
            score += 1
            reasons.append("包含广告/引流词")
        if any(pattern.search(text) for pattern in self._invite_patterns):
            score += 2
            reasons.append("疑似外部联系方式或群号")

        if score < 2:
            return None

        return {
            "rule_type": RuleType.LINK.value,
            "action": RuleAction.MUTE.value,
            "reason": "广告检测：" + "、".join(reasons),
            "score_delta": 2,
            "mute_seconds": 600,
            "delete_message": True,
        }
