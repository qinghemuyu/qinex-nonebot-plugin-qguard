from dataclasses import dataclass
import re

from nonebot_plugin_group_wiki.models import WikiArticle

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")
_STOP_TERMS = {
    "怎么",
    "怎么开",
    "如何",
    "什么",
    "为啥",
    "为什么",
    "问题",
    "一下",
    "使用",
    "设置",
    "配置",
    "教程",
    "可以",
    "不能",
    "不会",
}


@dataclass(slots=True)
class SearchHit:
    article: WikiArticle
    score: float
    snippet: str
    reference: str = ""


def extract_query_terms(query: str) -> list[str]:
    text = query.strip().lower()
    terms: set[str] = set()
    for token in _ASCII_RE.findall(text):
        if len(token) <= 24 and any(char.isalpha() for char in token):
            terms.add(token)
    for cjk_text in _CJK_RE.findall(text):
        if cjk_text not in _STOP_TERMS:
            terms.add(cjk_text)
        for size in (2, 3):
            if len(cjk_text) < size:
                continue
            for index in range(0, len(cjk_text) - size + 1):
                term = cjk_text[index : index + size]
                if term not in _STOP_TERMS:
                    terms.add(term)
    return sorted(terms, key=lambda item: (-len(item), item))


def score_article(query: str, article: WikiArticle, chunks: list[str]) -> SearchHit | None:
    terms = extract_query_terms(query)
    if not terms:
        return None
    title = article.title.lower()
    content = "\n".join(chunks or [article.summary, article.content_md]).lower()
    score = 0.0
    for term in terms:
        if term in title:
            score += 5 + len(term) * 0.2
        score += min(content.count(term), 5) * max(1, min(len(term), 4) / 2)
    if score <= 0:
        return None
    chunk = best_chunk(terms, chunks or [article.summary, article.content_md])
    snippet = format_snippet(chunk)
    return SearchHit(article=article, score=score + article.hit_count * 0.1, snippet=snippet, reference=reference_from_chunk(article, chunk))


def best_chunk(terms: list[str], chunks: list[str]) -> str:
    best = ""
    best_score = -1
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(lower.count(term) for term in terms)
        if score > best_score:
            best = chunk
            best_score = score
    return best.strip()


def format_snippet(chunk: str) -> str:
    return chunk.strip().replace("\n", " ")[:260]


def reference_from_chunk(article: WikiArticle, chunk: str) -> str:
    category = article.category or article.article_no or article.title
    for line in chunk.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if not heading or heading == article.title:
            continue
        return f"{category}#{heading}"
    return category
