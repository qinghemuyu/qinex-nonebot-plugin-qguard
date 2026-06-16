from collections import defaultdict, deque
from time import monotonic
from typing import Any, ClassVar

from nonebot_plugin_qguard.enums import RuleAction, RuleType


class AntiSpamService:
    _history: ClassVar[dict[tuple[int, int], deque[tuple[float, str]]]] = defaultdict(deque)
    _repeat_window_seconds = 12.0
    _burst_window_seconds = 6.0
    _repeat_threshold = 3
    _burst_threshold = 5

    def check(self, group_id: int, user_id: int, plain_text: str, now: float | None = None) -> dict[str, Any] | None:
        normalized = " ".join(plain_text.split()).strip().lower()
        if not normalized:
            return None

        current = monotonic() if now is None else now
        key = (group_id, user_id)
        history = self._history[key]

        while history and current - history[0][0] > self._repeat_window_seconds:
            history.popleft()
        history.append((current, normalized))

        repeat_count = sum(
            1
            for timestamp, message in history
            if message == normalized and current - timestamp <= self._repeat_window_seconds
        )
        burst_count = sum(1 for timestamp, _message in history if current - timestamp <= self._burst_window_seconds)

        if repeat_count >= self._repeat_threshold:
            return self._decision("刷屏检测：短时间重复发送相同内容。")
        if burst_count >= self._burst_threshold:
            return self._decision("刷屏检测：短时间连续发送消息过快。")
        return None

    @classmethod
    def reset(cls) -> None:
        cls._history.clear()

    @staticmethod
    def _decision(reason: str) -> dict[str, Any]:
        return {
            "rule_type": RuleType.SPAM.value,
            "action": RuleAction.MUTE.value,
            "reason": reason,
            "score_delta": 2,
            "mute_seconds": 300,
            "delete_message": True,
        }
