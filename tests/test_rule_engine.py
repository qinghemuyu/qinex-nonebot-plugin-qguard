import pytest

from nonebot_plugin_qguard.services.rule_engine import MessageContext, RuleEngine


@pytest.mark.asyncio
async def test_rule_engine_default_no_hit() -> None:
    decision = await RuleEngine().check(
        MessageContext(group_id=1, user_id=2, message_id=3, plain_text="hello", raw_message="hello")
    )
    assert not decision.hit
    assert decision.action == "none"
