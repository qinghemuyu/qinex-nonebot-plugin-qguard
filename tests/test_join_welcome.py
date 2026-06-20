from uuid import uuid4

import pytest

from nonebot_plugin_qguard.services.join_welcome_service import JoinWelcomeContext, JoinWelcomeService


class FakeOps:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str, str]] = []

    async def send_group_msg(self, group_id: int, message: str, message_category: str = "command"):
        self.messages.append((group_id, message, message_category))
        return {"message_id": len(self.messages)}


@pytest.mark.asyncio
async def test_join_welcome_disabled_by_default() -> None:
    group_id = 970000000 + (uuid4().int % 100000000)
    ops = FakeOps()

    sent = await JoinWelcomeService().send_welcome_if_enabled(
        ops,
        JoinWelcomeContext(group_id=group_id, user_id=12345, sub_type="invite", operator_id=67890),
    )

    assert not sent
    assert ops.messages == []


@pytest.mark.asyncio
async def test_join_welcome_invite_message_contains_sources_and_tips() -> None:
    group_id = 971000000 + (uuid4().int % 100000000)
    service = JoinWelcomeService()
    await service.set_enabled(group_id, 1, True)

    ops = FakeOps()
    sent = await service.send_welcome_if_enabled(
        ops,
        JoinWelcomeContext(group_id=group_id, user_id=12345, sub_type="invite", operator_id=67890),
    )

    assert sent
    assert len(ops.messages) == 1
    sent_group_id, message, category = ops.messages[0]
    assert sent_group_id == group_id
    assert category == "chat"
    assert "[CQ:at,qq=12345]" in message
    assert "进群方式：邀请入群" in message
    assert "邀请人：[CQ:at,qq=67890]" in message
    assert "审批人：无" in message
    assert "群公告" in message
    assert "群文件" in message
    assert "教程" in message
    assert "艾特机器人" in message


@pytest.mark.asyncio
async def test_join_welcome_approve_by_bot_is_qguard_auto_review() -> None:
    group_id = 972000000 + (uuid4().int % 100000000)
    service = JoinWelcomeService()
    await service.set_enabled(group_id, 1, True)

    ops = FakeOps()
    await service.send_welcome_if_enabled(
        ops,
        JoinWelcomeContext(
            group_id=group_id,
            user_id=12345,
            sub_type="approve",
            operator_id=3195276161,
            bot_self_id=3195276161,
        ),
    )

    message = ops.messages[0][1]
    assert "进群方式：申请入群" in message
    assert "邀请人：无" in message
    assert "审批人：QGuard 自动审核" in message


@pytest.mark.asyncio
async def test_join_welcome_template_default_reset() -> None:
    group_id = 973000000 + (uuid4().int % 100000000)
    service = JoinWelcomeService()

    custom = await service.set_template(group_id, 1, "欢迎 {user_id}")
    reset = await service.set_template(group_id, 1, "默认")

    assert custom.success
    assert reset.success
    assert "默认模板" in await service.status(group_id)
