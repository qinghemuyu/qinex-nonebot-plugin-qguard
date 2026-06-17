from nonebot_plugin_ai_core.service import AICoreService, get_ai_core

from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.services.schemas import AskResponse
from nonebot_plugin_group_wiki.services.search_service import WikiSearchService
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


class RAGService:
    def __init__(
        self,
        config: Config | None = None,
        search_service: WikiSearchService | None = None,
        ai_core: AICoreService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.search_service = search_service or WikiSearchService()
        self.ai_core = ai_core or get_ai_core()

    async def ask(self, question: str, *, group_id: int | None = None, user_id: int | None = None) -> AskResponse:
        hits = await self.search_service.search(question, group_id=group_id, limit=4)
        if not hits:
            return AskResponse(
                answer=f"知识库里暂时没有找到和“{question}”相关的内容。你可以换个关键词，或让管理员补充 QInEX 文档。",
                references=[],
                hits=[],
                ai_used=False,
            )
        references = [hit.article.article_no for hit in hits]
        if not self.config.group_wiki_enable_ai:
            answer = self._fallback_answer(question, hits)
            return AskResponse(answer=answer, references=references, hits=hits, ai_used=False)
        context = "\n\n".join(
            f"[{hit.article.article_no}] {hit.article.title}\n{hit.snippet or hit.article.summary}" for hit in hits
        )
        try:
            answer = await self.ai_core.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            f"你是 {self.config.group_wiki_software_name} 售后知识库助手。"
                            "只能根据给定知识库片段回答，不要编造知识库外的功能、价格、授权或承诺。"
                            "如果片段不足以回答，要明确说知识库没有足够信息。回答简洁，适合 QQ 群。"
                        ),
                    },
                    {"role": "user", "content": f"知识库片段：\n{context}\n\n用户问题：{question}"},
                ],
                user_id=user_id,
                group_id=group_id,
                purpose="group_wiki_ask",
                max_tokens=768,
                temperature=0.2,
            )
            return AskResponse(answer=answer, references=references, hits=hits, ai_used=True)
        except Exception:
            return AskResponse(answer=self._fallback_answer(question, hits), references=references, hits=hits, ai_used=False)

    @staticmethod
    def _fallback_answer(question: str, hits: list) -> str:
        first = hits[0]
        snippet = first.snippet or first.article.summary or split_text(first.article.content_md, chunk_size=260, overlap=0)[0]
        return f"知识库里和“{question}”最相关的是：{first.article.title}\n{snippet}"
