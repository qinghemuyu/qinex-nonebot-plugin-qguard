from __future__ import annotations

from dataclasses import dataclass
import re

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import get_session
from nonebot_plugin_support_bot.repositories.harassment_repo import SupportHarassmentRepo

ABUSE_PATTERNS = (
    "傻逼",
    "煞笔",
    "sb",
    "s b",
    "弱智",
    "智障",
    "脑残",
    "废物",
    "垃圾机器人",
    "垃圾ai",
    "垃圾客服",
    "你妈",
    "你m",
    "滚",
    "闭嘴",
    "爬",
    "狗东西",
)
TAUNT_PATTERNS = (
    "你行不行",
    "到底行不行",
    "真服了",
    "没用的东西",
    "叫爸爸",
    "出来挨打",
    "别装死",
    "机器人坏了",
    "ai坏了",
)
LOW_SIGNAL_RE = re.compile(r"^[\s?？!！。,.，~～…]+$")


@dataclass(frozen=True)
class HarassmentEvaluation:
    severity: int = 0
    reason: str = ""
    anger_score: int = 0
    score_delta: int = 0
    warned: bool = False

    @property
    def hit(self) -> bool:
        return self.severity > 0


class HarassmentService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    async def record_if_needed(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int,
        reply_state: str,
    ) -> HarassmentEvaluation:
        if not self.config.support_bot_harassment_enabled:
            return HarassmentEvaluation()
        if group_id is None or user_id in set(self.config.support_bot_admins):
            return HarassmentEvaluation()

        severity, reason = classify_harassment(text, reply_state)
        if severity <= 0:
            return HarassmentEvaluation()

        async with get_session() as session:
            item, score_delta, warned = await SupportHarassmentRepo(session).record(
                group_id=int(group_id),
                user_id=int(user_id),
                severity=severity,
                reason=reason,
                text=text,
                window_seconds=self.config.support_bot_harassment_window_seconds,
                score_threshold=self.config.support_bot_harassment_score_threshold,
                score_cooldown_seconds=self.config.support_bot_harassment_score_cooldown_seconds,
                base_score_delta=self.config.support_bot_harassment_score_delta,
                max_score_delta=self.config.support_bot_harassment_max_score_delta,
            )
            anger_score = item.anger_score
            await session.commit()

        return HarassmentEvaluation(
            severity=severity,
            reason=reason,
            anger_score=anger_score,
            score_delta=score_delta,
            warned=warned,
        )


def classify_harassment(text: str, reply_state: str) -> tuple[int, str]:
    normalized = _normalize(text)
    if not normalized:
        return 0, ""
    if any(pattern in normalized for pattern in ABUSE_PATTERNS):
        return 3, "辱骂智能客服"
    if any(pattern in normalized for pattern in TAUNT_PATTERNS):
        return 2, "挑衅智能客服"
    if LOW_SIGNAL_RE.fullmatch(text.strip()) and reply_state in {"out_of_scope", "no_answer", "collecting_issue"}:
        return 1, "无意义骚扰智能客服"
    if reply_state == "out_of_scope":
        return 1, "反复发送非 QInEX 问题"
    return 0, ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())
