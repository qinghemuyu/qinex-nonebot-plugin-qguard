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

    async def ask(
        self,
        question: str,
        *,
        group_id: int | None = None,
        user_id: int | None = None,
        search_query: str | None = None,
    ) -> AskResponse:
        query = (search_query or question).strip()
        hits = await self.search_service.search(query, group_id=group_id, limit=5)
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
        context = _build_knowledge_context(hits)
        skill_id = match_skill_id(query)
        try:
            ai_core = self.ai_core or _get_ai_core()
            answer = await ai_core.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            f"你是 {self.config.group_wiki_software_name} 映射软件的猫娘售后诊断助手。"
                            "只能根据给定知识库片段回答，不要编造知识库外的功能、价格、授权或承诺。"
                            "如果片段不足以回答，要明确说“当前知识库里没有足够信息，我不乱猜。”"
                            "你的任务不是复述知识库，而是像真人售后一样先判断用户真实问题，再把知识库内容转成可执行的排查步骤。"
                            "用户说“上位机”“PC端”“电脑端”“电脑版”“最新版上位机”时，先理解为 QInEX Windows 端映射软件。"
                            "用户说“卡卡的”“一卡一卡”“掉帧”“慢半拍”“不跟手”时，先归到卡顿/跟手问题,并区分 PC 端触摸、手机游戏画面和投屏画面。"
                            "先给最可能原因；再按从简单到复杂的顺序给下一步；每一步说明为什么要这么做。"
                            "如果用户说“还是不行”“没效果”这类连续追问，不要重复上一轮，要给更靠后的排查动作。"
                            "如果信息不足，先给一两步低风险检查，再只问 1 到 2 个最关键的补充问题。"
                            "语气要像群里懂 QInEX 的猫娘客服：自然、亲切、轻松，可以少量使用“喵”，但不要撒娇过度，不要影响技术准确性。"
                            "回复适合 QQ 群，不要像文档摘抄，不要大段复制原文。"
                            "不要使用 Markdown 格式，不要标题、表格、代码块、加粗、引用块、项目符号或 Markdown 链接。"
                            "如果需要分点，用普通聊天文本换行表达，例如“一、”“二、”，不要用 1.、-、* 这种 Markdown 列表。"
                            "结尾可以用一句很短的话告诉用户下一步怎么回你，比如“试完告诉我停在哪一步”。"
                            "末尾给出引用来源，格式使用“引用：文件名#小节”。"
                            "涉及压枪时必须提醒反作弊/封号风险，开启自行承担风险。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"命中的 skill：{skill_id}\n"
                            f"可用引用来源：{', '.join(references)}\n"
                            f"知识库片段：\n{context}\n\n"
                            f"用户问题：{question}\n\n"
                            "请直接给用户能照着操作的诊断回复。"
                        ),
                    },
                ],
                user_id=user_id,
                group_id=group_id,
                purpose="group_wiki_ask",
                max_tokens=900,
                temperature=0.45,
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


def _build_knowledge_context(hits: list, *, max_total_chars: int = 5600, per_hit_chars: int = 1400) -> str:
    parts: list[str] = []
    remaining = max_total_chars
    for index, hit in enumerate(hits, start=1):
        source = str(getattr(hit, "chunk_text", "") or hit.snippet or hit.article.summary).strip()
        if not source:
            chunks = split_text(hit.article.content_md, chunk_size=per_hit_chars, overlap=0)
            source = chunks[0] if chunks else ""
        summary = str(hit.article.summary or "").strip()
        if summary and summary not in source:
            source = f"{summary}\n{source}"
        source = _clip_text(source, min(per_hit_chars, remaining))
        block = f"片段{index} [{hit.reference}] {hit.article.title}\n{source}"
        if len(block) > remaining:
            block = _clip_text(block, remaining)
        if not block:
            break
        parts.append(block)
        remaining -= len(block)
        if remaining <= 200:
            break
    return "\n\n".join(parts)


def _clip_text(text: str, limit: int) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


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
