from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.models.message_cache import MessageCache
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo
from nonebot_plugin_qguard.services.message_cache_service import MessageCacheService
from nonebot_plugin_qguard.utils.formatter import format_cached_message_detail


@pytest.mark.asyncio
async def test_message_cache_get_in_group() -> None:
    group_id = 870000000 + (uuid4().int % 100000000)
    other_group_id = 871000000 + (uuid4().int % 100000000)
    message_id = 700000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)

    item = MessageCache(
        message_id=message_id,
        group_id=group_id,
        user_id=user_id,
        plain_text="hello cache",
        raw_message_json="[]",
        image_count=1,
        at_count=2,
        link_count=3,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    async with get_session() as session:
        await MessageCacheRepo(session).upsert(item)
        await session.commit()

    found = await MessageCacheService().get_in_group(group_id, message_id)
    missing = await MessageCacheService().get_in_group(other_group_id, message_id)

    assert found is not None
    assert found.user_id == user_id
    assert missing is None
    detail = format_cached_message_detail(found)
    assert str(message_id) in detail
    assert str(user_id) in detail
    assert "hello cache" in detail
    assert "1" in detail
    assert "2" in detail
    assert "3" in detail
