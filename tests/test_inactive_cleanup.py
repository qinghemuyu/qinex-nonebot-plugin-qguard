from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.models.message_cache import MessageCache
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo
from nonebot_plugin_qguard.services.bulk_recall_service import BulkRecallService
from nonebot_plugin_qguard.services.inactive_cleanup_service import (
    InactiveCleanupService,
    deserialize_cleanup_reminder_days,
    format_cleanup_reminder_days,
    parse_cleanup_day_token,
    serialize_cleanup_reminder_days,
)


class FakeBot:
    def __init__(self, members=None) -> None:
        self.self_id = "42"
        self.members = members or []
        self.private_messages: list[tuple[int, str]] = []
        self.kicked: list[tuple[int, int, bool]] = []

    async def get_group_member_list(self, group_id: int):
        return self.members

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        for member in self.members:
            if int(member["user_id"]) == user_id:
                return member
        return {"user_id": user_id, "role": "member"}

    async def send_private_msg(self, user_id: int, message: str) -> None:
        self.private_messages.append((user_id, message))

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        self.kicked.append((group_id, user_id, reject_add_request))


class FakeOps:
    def __init__(self) -> None:
        self.deleted: list[int] = []

    async def delete_msg(self, message_id: int) -> None:
        self.deleted.append(message_id)

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        return {"user_id": user_id, "role": "admin"}


def test_cleanup_day_helpers() -> None:
    assert parse_cleanup_day_token("30") == 30
    assert parse_cleanup_day_token("30d") == 30
    assert serialize_cleanup_reminder_days([60, 30, 30]) == "30,60"
    assert deserialize_cleanup_reminder_days("60,30") == [30, 60]
    assert format_cleanup_reminder_days([30, 60]) == "30天、60天"


@pytest.mark.asyncio
async def test_inactive_cleanup_reminds_and_kicks_once() -> None:
    group_id = 996000000 + (uuid4().int % 100000000)
    now = datetime(2026, 6, 20, 0, 0, 0)
    members = [
        {"user_id": 1001, "role": "member", "last_sent_time": int((now - timedelta(days=31)).timestamp())},
        {"user_id": 1002, "role": "member", "last_sent_time": int((now - timedelta(days=61)).timestamp())},
        {"user_id": 1003, "role": "member", "last_sent_time": int((now - timedelta(days=91)).timestamp())},
        {"user_id": 1004, "role": "admin", "last_sent_time": int((now - timedelta(days=120)).timestamp())},
        {"user_id": 42, "role": "member", "last_sent_time": int((now - timedelta(days=120)).timestamp())},
    ]
    bot = FakeBot(members)
    service = InactiveCleanupService()

    await service.set_enabled(group_id, 1, True)
    result = await service.run_group(bot, group_id, now=now)

    assert result.checked == 4
    assert result.reminded == 2
    assert result.kicked == 1
    assert [item[0] for item in bot.private_messages] == [1001, 1002]
    assert bot.kicked == [(group_id, 1003, False)]

    second = await service.run_group(bot, group_id, now=now)

    assert second.reminded == 0
    assert second.kicked == 0
    assert len(bot.private_messages) == 2
    assert bot.kicked == [(group_id, 1003, False)]


@pytest.mark.asyncio
async def test_bulk_recall_uses_command_then_cached_messages() -> None:
    group_id = 997000000 + (uuid4().int % 100000000)
    message_base = 600000000 + (uuid4().int % 100000000)
    command_message_id = message_base + 99
    now = datetime(2026, 6, 20, 0, 0, 0)
    async with get_session() as session:
        repo = MessageCacheRepo(session)
        message_ids = list(range(message_base, message_base + 5))
        for index, message_id in enumerate(message_ids, start=1):
            await repo.upsert(
                MessageCache(
                    message_id=message_id,
                    group_id=group_id,
                    user_id=2000 + index,
                    plain_text=f"msg {message_id}",
                    raw_message_json="[]",
                    image_count=0,
                    at_count=0,
                    link_count=0,
                    created_at=now + timedelta(seconds=index),
                    updated_at=now + timedelta(seconds=index),
                    expires_at=now + timedelta(days=7),
                )
            )
        await session.commit()

    ops = FakeOps()
    result = await BulkRecallService().recall_recent(
        ops,
        group_id=group_id,
        operator_id=1,
        command_message_id=command_message_id,
        count=3,
    )

    assert result.success
    assert ops.deleted == [command_message_id, message_ids[-1], message_ids[-2]]
    assert result.attempted == 3
