from dataclasses import dataclass

from nonebot_plugin_group_wiki.utils.rerank import SearchHit


@dataclass(slots=True)
class AskResponse:
    answer: str
    references: list[str]
    hits: list[SearchHit]
    ai_used: bool = False
