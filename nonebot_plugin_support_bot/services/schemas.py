from pydantic import BaseModel, Field


class SupportIntent(BaseModel):
    is_support_request: bool = True
    intent: str = "support"
    confidence: float = 0.8
    product: str | None = "QInEX"
    skill: str = "unknown"
    issue_type: str = "unknown"
    urgency: str = "normal"
    need_log: bool = False
    need_screenshot: bool = False
    need_version: bool = False
    need_config: bool = False
    should_search_wiki: bool = True
    reply_strategy: str = "answer"
    missing_fields: list[str] = Field(default_factory=list)


class SupportReply(BaseModel):
    text: str
    state: str = "answering"
    references: list[str] = Field(default_factory=list)
    ai_used: bool = False
    no_answer_id: str = ""
    owner_escalation: bool = False
    owner_escalation_summary: str = ""
    owner_escalation_turns: int = 0
    harassment_anger: int = 0
    harassment_score_delta: int = 0
    harassment_reason: str = ""
