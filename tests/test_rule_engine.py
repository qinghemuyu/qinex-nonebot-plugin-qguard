import pytest
from uuid import uuid4

from nonebot_plugin_qguard.commands.rule import _parse_rule_ids
from nonebot_plugin_qguard.enums import RuleAction, RuleType
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.rule_repo import RuleRepo
from nonebot_plugin_qguard.services.rule_engine import MessageContext, RuleEngine


@pytest.mark.asyncio
async def test_rule_engine_default_no_hit() -> None:
    decision = await RuleEngine().check(
        MessageContext(group_id=1, user_id=2, message_id=3, plain_text="hello", raw_message="hello")
    )
    assert not decision.hit
    assert decision.action == "none"


def test_parse_rule_ids_accepts_batch_formats() -> None:
    assert _parse_rule_ids(["10,6,19,18,17,16,14,12,11"]) == [10, 6, 19, 18, 17, 16, 14, 12, 11]
    assert _parse_rule_ids(["#10", "6，19", "18、17", "10"]) == [10, 6, 19, 18, 17]


@pytest.mark.asyncio
async def test_rule_engine_keyword_hit() -> None:
    group_id = 900000000 + (uuid4().int % 100000000)
    pattern = f"spam-word-{uuid4().hex}"
    async with get_session() as session:
        item = await RuleRepo(session).create(
            group_id=group_id,
            rule_type=RuleType.KEYWORD,
            pattern=pattern,
            action=RuleAction.WARN,
            created_by=1,
        )
        await session.commit()

    decision = await RuleEngine().check(
        MessageContext(group_id=group_id, user_id=2, message_id=3, plain_text=f"hello {pattern}", raw_message="hello")
    )
    assert decision.hit
    assert decision.rule_id == item.id
    assert decision.action == RuleAction.WARN.value
