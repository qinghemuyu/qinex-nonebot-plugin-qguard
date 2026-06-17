from pydantic import BaseModel, Field


class SupportIntent(BaseModel):
    is_support_request: bool = True
    intent: str = "support"
    confidence: float = 0.8
    product: str | None = "QInEX"
    issue_type: str = "unknown"
    urgency: str = "normal"
    need_log: bool = False
    need_screenshot: bool = False
    need_version: bool = False
    need_config: bool = False
    should_search_wiki: bool = True
    should_diagnose_log: bool = False
    should_create_ticket: bool = False
    reply_strategy: str = "answer"
    missing_fields: list[str] = Field(default_factory=list)


class SupportReply(BaseModel):
    text: str
    state: str = "answering"
    ticket_no: str = ""
    references: list[str] = Field(default_factory=list)
    diagnosis_no: str = ""
    ai_used: bool = False
