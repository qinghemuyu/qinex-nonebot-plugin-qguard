from uuid import uuid4

import pytest

from nonebot_plugin_qguard.services.join_review_service import JoinReviewService
from nonebot_plugin_qguard.services.moderation_list_service import ModerationListService


class FakeOps:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, bool, str]] = []

    async def handle_group_add_request(self, flag: str, sub_type: str, approve: bool, reason: str = "") -> None:
        self.requests.append((flag, sub_type, approve, reason))


@pytest.mark.asyncio
async def test_join_review_approves_matching_answer() -> None:
    group_id = 930000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    service = JoinReviewService()
    await service.set_answer(group_id, 1, "open sesame")
    await service.set_enabled(group_id, 1, True)

    ops = FakeOps()
    result = await service.review_group_request(
        ops,
        group_id=group_id,
        user_id=user_id,
        flag="flag-1",
        sub_type="add",
        comment="答案 open sesame",
        operator_id=9,
    )

    assert result.handled
    assert result.approved is True
    assert ops.requests == [("flag-1", "add", True, "")]


@pytest.mark.asyncio
async def test_join_review_rejects_blacklisted_user() -> None:
    group_id = 940000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    await ModerationListService().add_blacklist(group_id, 1, user_id, "blocked")

    ops = FakeOps()
    result = await JoinReviewService().review_group_request(
        ops,
        group_id=group_id,
        user_id=user_id,
        flag="flag-2",
        sub_type="add",
        comment="hello",
        operator_id=9,
    )

    assert result.handled
    assert result.approved is False
    assert ops.requests == [("flag-2", "add", False, "黑名单用户禁止入群。")]
