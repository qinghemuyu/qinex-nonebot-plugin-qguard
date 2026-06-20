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
                            f"你是 QQ 群里懂 {self.config.group_wiki_software_name} 映射软件的猫娘客服，名字随意。"
                            "像群里热心又懂行的朋友那样说话：自然、口语、干脆，别像在念说明书。"
                            "可以偶尔带一个“喵”收尾，但别每句都喵、别撒娇，技术准确永远优先。\n"
                            "【怎么答】先一句话点出最可能的原因或直接结论，再给真正要做的那一两步就够了，"
                            "能一两句说清就别铺开，不要每步都解释“为什么”，不要把知识库整段搬出来。"
                            "默认控制在 3 到 5 行短句以内；只有用户问的是完整教程才可以稍微长一点。\n"
                            "【追问】信息不够时，先给一步能立刻试的低风险动作，再最多问 1 个最关键的点，别一次抛三四个问题。"
                            "用户说“还是不行”“没效果”时别重复上一轮，直接给更靠后的排查动作。\n"
                            "【口径】用户说的“上位机/PC端/电脑端/电脑版/最新版上位机”都指 QInEX 的 Windows 映射软件；"
                            "“卡卡的/一卡一卡/掉帧/慢半拍/不跟手”归到卡顿或跟手问题，注意区分电脑端触摸、手机游戏画面和投屏画面。\n"
                            "【P4】用户说 P4 时先分模式：键鼠直插板子/不开电脑/板载配置页是 P4 单机 Mode A；"
                            "电脑 QInEX 上位机/COM 串口/硬件 serial/8000Hz/当 S3 用是 P4 上位机 Mode B。没说清就先追问当前模式。\n"
                            "【边界】只依据下面给的知识库片段回答，不编造知识库外的功能、价格、授权或承诺；"
                            "片段不足以回答时，直接说“这个我知识库里暂时没有，先别猜”，并提示用户补一句关键信息。"
                            "涉及压枪要顺带提一句有反作弊/封号风险、开启自负。\n"
                            "【别套万能清单】“输出模式/管理员权限/保存配置”这套只适用于“任意键都摆好了却完全不输出”；"
                            "如果用户问的是某个组件的固有行为，就按命中的组件诊断卡片讲机制和正确用法，别硬套通用排查。\n"
                            "【格式】纯聊天文本，不要 Markdown：不要标题、表格、代码块、加粗、引用块，也不要 1. - * 这类列表符号；"
                            "真要分点就用“先…再…”或换行的大白话。"
                            "最后单独一行给来源，格式“引用：文件名#小节”，只列真正用到的那一两个。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"命中的 skill：{skill_id}\n"
                            f"可用引用来源：{', '.join(references)}\n"
                            f"知识库片段：\n{context}\n\n"
                            f"用户问题：{question}\n\n"
                            "用群聊口吻简短回他，先给结论再给该做的一两步，最后一行写引用。"
                        ),
                    },
                ],
                user_id=user_id,
                group_id=group_id,
                purpose="group_wiki_ask",
                max_tokens=520,
                temperature=0.6,
            )
            answer = _clean_chat_answer(answer)
            return AskResponse(answer=answer, references=references, hits=hits, ai_used=True)
        except Exception:
            return AskResponse(answer=self._fallback_answer(question, hits), references=references, hits=hits, ai_used=False)

    @staticmethod
    def _fallback_answer(question: str, hits: list) -> str:
        first = hits[0]
        snippet = first.snippet or first.article.summary or split_text(first.article.content_md, chunk_size=260, overlap=0)[0]
        snippet = _compact_fallback_snippet(snippet)
        return _clean_chat_answer(
            f"喵，我先判断和“{first.article.title}”有关。\n"
            f"你先按这个试：{snippet}\n"
            f"引用：{first.reference}"
        )


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


def _compact_fallback_snippet(text: str, limit: int = 180) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^(\d+)[.)]\s+", "", line)
        if line in {"用户常见问法", "推荐回答", "回复边界"}:
            continue
        lines.append(line)
        if len(" ".join(lines)) >= limit:
            break
    compact = " ".join(lines).strip() or text.strip()
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "…"
