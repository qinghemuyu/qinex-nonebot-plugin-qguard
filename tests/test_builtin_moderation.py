from uuid import uuid4

import pytest

from nonebot_plugin_qguard.enums import RuleAction, RuleType
from nonebot_plugin_qguard.services.ad_keyword_defaults import DEFAULT_AD_KEYWORDS
from nonebot_plugin_qguard.services.ad_keyword_service import AdKeywordService
from nonebot_plugin_qguard.services.anti_spam_service import AntiSpamService
from nonebot_plugin_qguard.services.group_config_service import GroupConfigService
from nonebot_plugin_qguard.services.rule_engine import MessageContext, RuleEngine


def _context(group_id: int, user_id: int, message_id: int, text: str) -> MessageContext:
    return MessageContext(
        group_id=group_id,
        user_id=user_id,
        message_id=message_id,
        plain_text=text,
        raw_message=text,
        link_count=text.count("http://") + text.count("https://"),
    )


@pytest.mark.asyncio
async def test_anti_ad_disabled_by_default() -> None:
    group_id = 996000000 + (uuid4().int % 100000000)

    decision = await RuleEngine().check(_context(group_id, 2, 1, "加群 123456 https://example.com"))

    assert not decision.hit


@pytest.mark.asyncio
async def test_anti_ad_detects_invite_link() -> None:
    group_id = 997000000 + (uuid4().int % 100000000)
    await GroupConfigService().set_anti_ad_enabled(group_id, 1, True)

    decision = await RuleEngine().check(_context(group_id, 2, 1, "加群 123456 https://example.com"))

    assert decision.hit
    assert decision.rule_type == RuleType.LINK.value
    assert decision.action == RuleAction.MUTE.value
    assert decision.delete_message
    assert decision.mute_seconds == 600
    assert decision.score_delta == 2


@pytest.mark.asyncio
async def test_default_ad_keywords_are_seeded_idempotently() -> None:
    group_id = 995000000 + (uuid4().int % 100000000)
    service = AdKeywordService()

    created = await service.ensure_defaults(group_id)
    created_again = await service.ensure_defaults(group_id)

    assert created == len(DEFAULT_AD_KEYWORDS)
    assert created_again == 0
    assert await service.count(group_id) == len(DEFAULT_AD_KEYWORDS)


@pytest.mark.asyncio
async def test_removed_default_ad_keyword_stays_disabled() -> None:
    group_id = 994000000 + (uuid4().int % 100000000)
    service = AdKeywordService()
    await service.ensure_defaults(group_id)
    items = await service.list(group_id, limit=500)
    keyword_item = next(item for item in items if item.keyword == "刷单")

    remove_result = await service.remove(group_id, 1, keyword_item.id)
    created_again = await service.ensure_defaults(group_id)
    refreshed = await service.list(group_id, limit=500)
    same_keyword_items = [item for item in refreshed if item.keyword == "刷单"]

    assert remove_result.success
    assert created_again == 0
    assert len(same_keyword_items) == 1
    assert not same_keyword_items[0].enabled


@pytest.mark.asyncio
async def test_default_ad_keyword_hits_after_enable() -> None:
    group_id = 993000000 + (uuid4().int % 100000000)
    await GroupConfigService().set_anti_ad_enabled(group_id, 1, True)

    decision = await RuleEngine().check(_context(group_id, 2, 1, "刷单任务单，佣金秒结"))

    assert decision.hit
    assert decision.reason.startswith("广告检测：")


@pytest.mark.asyncio
async def test_custom_ad_keyword_hits_and_can_be_removed() -> None:
    group_id = 999000000 + (uuid4().int % 100000000)
    keyword = f"custom-ad-{uuid4().hex}"
    await GroupConfigService().set_anti_ad_enabled(group_id, 1, True)

    add_result = await AdKeywordService().add(group_id, 1, keyword)
    assert add_result.success

    hit = await RuleEngine().check(_context(group_id, 2, 1, f"hello {keyword}"))
    assert hit.hit
    assert hit.rule_type == RuleType.LINK.value
    assert hit.reason.startswith("广告检测：")

    items = await AdKeywordService().list(group_id)
    item = next(item for item in items if item.keyword == keyword)
    remove_result = await AdKeywordService().remove(group_id, 1, item.id)
    assert remove_result.success

    miss = await RuleEngine().check(_context(group_id, 2, 2, f"hello {keyword}"))
    assert not miss.hit


@pytest.mark.asyncio
async def test_anti_spam_detects_repeated_messages() -> None:
    AntiSpamService.reset()
    group_id = 998000000 + (uuid4().int % 100000000)
    user_id = 10000 + (uuid4().int % 100000)
    await GroupConfigService().set_anti_spam_enabled(group_id, 1, True)

    first = await RuleEngine().check(_context(group_id, user_id, 1, "repeat me"))
    second = await RuleEngine().check(_context(group_id, user_id, 2, "repeat me"))
    third = await RuleEngine().check(_context(group_id, user_id, 3, "repeat me"))

    assert not first.hit
    assert not second.hit
    assert third.hit
    assert third.rule_type == RuleType.SPAM.value
    assert third.action == RuleAction.MUTE.value
    assert third.delete_message
    assert third.mute_seconds == 300
