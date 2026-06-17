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


@pytest.mark.asyncio
async def test_join_review_rejects_empty_comment() -> None:
    group_id = 941000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    service = JoinReviewService()
    service.reset_request_history()
    await service.set_enabled(group_id, 1, True)

    ops = FakeOps()
    result = await service.review_group_request(
        ops,
        group_id=group_id,
        user_id=user_id,
        flag="flag-empty",
        sub_type="add",
        comment=" ",
        operator_id=9,
    )

    assert result.handled
    assert result.approved is False
    assert ops.requests == [("flag-empty", "add", False, "入群申请理由为空。")]


@pytest.mark.asyncio
async def test_join_review_rejects_ad_comment_before_answer() -> None:
    group_id = 942000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    service = JoinReviewService()
    service.reset_request_history()
    await service.set_answer(group_id, 1, "open sesame")
    await service.set_enabled(group_id, 1, True)

    ops = FakeOps()
    result = await service.review_group_request(
        ops,
        group_id=group_id,
        user_id=user_id,
        flag="flag-ad",
        sub_type="add",
        comment="open sesame 加群 123456 https://example.com",
        operator_id=9,
    )

    assert result.handled
    assert result.approved is False
    assert ops.requests == [("flag-ad", "add", False, "入群申请包含广告或引流内容。")]


@pytest.mark.asyncio
async def test_join_review_rejects_repeated_requests() -> None:
    group_id = 943000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    service = JoinReviewService()
    service.reset_request_history()
    await service.set_enabled(group_id, 1, True)

    for index in range(2):
        result = await service.review_group_request(
            FakeOps(),
            group_id=group_id,
            user_id=user_id,
            flag=f"flag-repeat-{index}",
            sub_type="add",
            comment="hello",
            operator_id=9,
        )
        assert not result.handled

    ops = FakeOps()
    result = await service.review_group_request(
        ops,
        group_id=group_id,
        user_id=user_id,
        flag="flag-repeat-3",
        sub_type="add",
        comment="hello",
        operator_id=9,
    )

    assert result.handled
    assert result.approved is False
    assert ops.requests == [("flag-repeat-3", "add", False, "入群申请过于频繁。")]
