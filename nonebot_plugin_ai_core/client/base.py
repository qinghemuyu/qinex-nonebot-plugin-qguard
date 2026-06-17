from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class AIClientResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw: dict | None = None


class BaseAIClient(Protocol):
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
    ) -> AIClientResponse:
        ...
