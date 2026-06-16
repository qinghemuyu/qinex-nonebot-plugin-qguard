from uuid import uuid4

import pytest

from nonebot_plugin_qguard.enums import RuleAction, RuleType
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
