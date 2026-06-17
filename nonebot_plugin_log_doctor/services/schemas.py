from pydantic import BaseModel, Field


class DiagnosisResult(BaseModel):
    title: str = Field(description="一句话错误标题")
    category: str = Field(description="错误分类")
    severity: str = Field(description="low/medium/high/critical")
    confidence: float = Field(ge=0, le=1)
    root_cause: str
    evidence: list[str] = Field(default_factory=list)
    fix_steps: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    need_more_info: bool = False
    questions: list[str] = Field(default_factory=list)
    related_keywords: list[str] = Field(default_factory=list)
    should_add_to_wiki: bool = False


class DiagnosisResponse(BaseModel):
    result: DiagnosisResult
    record_no: str
    ai_used: bool = False
    source_type: str = "command"
