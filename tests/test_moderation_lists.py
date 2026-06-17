from uuid import uuid4

import pytest

from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.blacklist_repo import BlacklistRepo
from nonebot_plugin_qguard.repositories.whitelist_repo import WhitelistRepo
from nonebot_plugin_qguard.services.moderation_list_service import ModerationListService


@pytest.mark.asyncio
async def test_whitelist_add_remove_and_list() -> None:
    group_id = 910000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)

    service = ModerationListService()
    result = await service.add_whitelist(group_id, 1, user_id, "trusted")
    assert result.success
    assert (user_id, "trusted") in await service.list_whitelist(group_id)

    async with get_session() as session:
        assert await WhitelistRepo(session).is_whitelisted(group_id, user_id)

    result = await service.remove_whitelist(group_id, 1, user_id)
    assert result.success
    assert await service.list_whitelist(group_id) == []


@pytest.mark.asyncio
async def test_blacklist_add_remove_and_list() -> None:
    group_id = 920000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)

    service = ModerationListService()
    result = await service.add_blacklist(group_id, 1, user_id, "blocked")
    assert result.success
    assert (user_id, "blocked") in await service.list_blacklist(group_id)

    async with get_session() as session:
        assert await BlacklistRepo(session).is_blacklisted(group_id, user_id)

    result = await service.remove_blacklist(group_id, 1, user_id)
    assert result.success
    assert await service.list_blacklist(group_id) == []


@pytest.mark.asyncio
async def test_global_blacklist_matches_any_group() -> None:
    group_id = 921000000 + (uuid4().int % 100000000)
    other_group_id = 922000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)

    service = ModerationListService()
    result = await service.add_blacklist(None, 1, user_id, "global blocked")
    assert result.success
    assert (user_id, "global blocked") in await service.list_global_blacklist()

    async with get_session() as session:
        repo = BlacklistRepo(session)
        assert await repo.is_blacklisted(group_id, user_id)
        assert await repo.is_blacklisted(other_group_id, user_id)

    result = await service.remove_blacklist(None, 1, user_id)
    assert result.success
    assert await service.list_global_blacklist() == []
