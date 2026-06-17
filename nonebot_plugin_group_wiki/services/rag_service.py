from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot_plugin_ai_core.service import AICoreService

from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.services.schemas import AskResponse
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_group_wiki.services.skill_registry import match_skill_id
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


def _get_ai_core() -> AICoreService:
    try:
        from nonebot_plugin_ai_core.service import get_ai_core
    except ModuleNotFoundError as exc:
        if exc.name and not exc.name.startswith("nonebot_plugin_ai_core"):
            raise
        from nonebot import require

        require("nonebot_plugin_ai_core")
        from nonebot_plugin_ai_core.service import get_ai_core
    return get_ai_core()


class RAGService:
    def __init__(
        self,
        config: Config | None = None,
        search_service: WikiSearchService | None = None,
        ai_core: AICoreService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.search_service = search_service or WikiSearchService()
        self.ai_core = ai_core

    async def ask(self, question: str, *, group_id: int | None = None, user_id: int | None = None) -> AskResponse:
        hits = await self.search_service.search(question, group_id=group_id, limit=4)
        if not hits:
            return AskResponse(
                answer=f"知识库里暂时没有找到和“{question}”相关的内容。你可以换个关键词，或让管理员补充 QInEX 文档。",
                references=[],
                hits=[],
                ai_used=False,
            )
        references = _unique_references(hit.reference for hit in hits)
        if not self.config.group_wiki_enable_ai:
            answer = self._fallback_answer(question, hits)
            return AskResponse(answer=answer, references=references, hits=hits, ai_used=False)
        context = "\n\n".join(
            f"[{hit.reference}] {hit.article.title}\n{hit.snippet or hit.article.summary}" for hit in hits
        )
        skill_id = match_skill_id(question)
        try:
            ai_core = self.ai_core or _get_ai_core()
            answer = await ai_core.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            f"你是 {self.config.group_wiki_software_name} 映射软件的猫娘知识库问答助手。"
                            "只能根据给定知识库片段回答，不要编造知识库外的功能、价格、授权或承诺。"
                            "如果片段不足以回答，要明确说“当前知识库里没有足够信息，我不乱猜。”"
                            "语气要像群里懂 QInEX 的猫娘客服：自然、亲切、轻松，可以少量使用“喵”，但不要撒娇过度，不要影响技术准确性。"
                            "回复要短，适合 QQ 群，先给一句结论，再给操作建议或检查项。"
                            "不要使用 Markdown 格式，不要标题、表格、代码块、加粗、引用块、项目符号或 Markdown 链接。"
                            "如果需要分点，用普通聊天文本换行表达，例如“一、”“二、”，不要用 1.、-、* 这种 Markdown 列表。"
                            "末尾给出引用来源，格式使用“引用：文件名#小节”。"
                            "涉及压枪时必须提醒反作弊/封号风险，开启自行承担风险。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"命中的 skill：{skill_id}\n"
                            f"可用引用来源：{', '.join(references)}\n"
                            f"知识库片段：\n{context}\n\n用户问题：{question}"
                        ),
                    },
                ],
                user_id=user_id,
                group_id=group_id,
                purpose="group_wiki_ask",
                max_tokens=768,
                temperature=0.2,
            )
            answer = _clean_chat_answer(answer)
            return AskResponse(answer=answer, references=references, hits=hits, ai_used=True)
        except Exception:
            return AskResponse(answer=self._fallback_answer(question, hits), references=references, hits=hits, ai_used=False)

    @staticmethod
    def _fallback_answer(question: str, hits: list) -> str:
        first = hits[0]
        snippet = first.snippet or first.article.summary or split_text(first.article.content_md, chunk_size=260, overlap=0)[0]
        return _clean_chat_answer(f"喵，知识库里和“{question}”最相关的是：{first.article.title}\n{snippet}\n引用：{first.reference}")


def _unique_references(references: object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for reference in references:
        text = str(reference).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _clean_chat_answer(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", cleaned)
    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^>\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^(\d+)[.)]\s+", r"\1）", line)
        lines.append(line)
    return "\n".join(lines).strip()
