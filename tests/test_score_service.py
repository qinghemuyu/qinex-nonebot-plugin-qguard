from types import SimpleNamespace
from uuid import uuid4

import pytest

from nonebot_plugin_qguard.enums import RuleAction
from nonebot_plugin_qguard.services.rule_engine import ModerationDecision
from nonebot_plugin_qguard.services.score_service import ScoreService, choose_score_penalty


class FakeOps:
    def __init__(self, operator_id: int) -> None:
        self.operator_id = operator_id
        self.muted: list[tuple[int, int, int]] = []
        self.kicked: list[tuple[int, int, bool]] = []

    async def mute(self, group_id: int, user_id: int, seconds: int) -> None:
        self.muted.append((group_id, user_id, seconds))

    async def kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        self.kicked.append((group_id, user_id, reject_add_request))

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        role = "admin" if user_id == self.operator_id else "member"
        return {"user_id": user_id, "role": role}


def test_choose_score_penalty() -> None:
    assert choose_score_penalty(2, 3, 600).action == RuleAction.MUTE
    assert choose_score_penalty(5, 6, 600).seconds == 3600
    assert choose_score_penalty(9, 10, 600).action == RuleAction.KICK
    assert choose_score_penalty(3, 4, 600) is None


@pytest.mark.asyncio
async def test_score_crossing_threshold_mutes() -> None:
    group_id = 970000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    operator_id = 999999
    event = SimpleNamespace(group_id=group_id, user_id=user_id, message_id=34567)
    decision = ModerationDecision(hit=True, action=RuleAction.WARN.value, reason="rule", score_delta=3)

    ops = FakeOps(operator_id)
    result = await ScoreService().apply_decision_score(ops, operator_id, event, decision)

    assert result.previous_score == 0
    assert result.current_score == 3
    assert result.penalty_action == RuleAction.MUTE.value
    assert ops.muted == [(group_id, user_id, 600)]


@pytest.mark.asyncio
async def test_score_reset() -> None:
    group_id = 980000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    operator_id = 999999
    event = SimpleNamespace(group_id=group_id, user_id=user_id, message_id=45678)
    decision = ModerationDecision(hit=True, action=RuleAction.DELETE.value, reason="rule", score_delta=2)

    await ScoreService().apply_decision_score(FakeOps(operator_id), operator_id, event, decision)
    await ScoreService().reset_score(group_id, operator_id, user_id)
    result = await ScoreService().get_score(group_id, user_id)

    assert result.current_score == 0
