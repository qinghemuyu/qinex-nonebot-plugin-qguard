from typing import Any

from pydantic import BaseModel


class MessageContext(BaseModel):
    group_id: int
    user_id: int
    message_id: int
    plain_text: str
    raw_message: Any
    image_count: int = 0
    at_count: int = 0
    link_count: int = 0
    is_new_member: bool = False


class ModerationDecision(BaseModel):
    hit: bool
    rule_id: int | None = None
    rule_type: str | None = None
    action: str = "none"
    reason: str = ""
    score_delta: int = 0
    mute_seconds: int = 0
    delete_message: bool = False


class RuleEngine:
    async def check(self, context: MessageContext) -> ModerationDecision:
        return ModerationDecision(hit=False)
