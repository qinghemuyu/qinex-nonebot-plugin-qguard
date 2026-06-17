from dataclasses import dataclass
import re

from nonebot_plugin_group_wiki.models import WikiArticle

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")


@dataclass(slots=True)
class SearchHit:
    article: WikiArticle
    score: float
    snippet: str


def extract_query_terms(query: str) -> list[str]:
    text = query.strip().lower()
    terms: set[str] = set()
    for token in _ASCII_RE.findall(text):
        if len(token) <= 24 and any(char.isalpha() for char in token):
            terms.add(token)
    for cjk_text in _CJK_RE.findall(text):
        terms.add(cjk_text)
        for size in (2, 3):
            if len(cjk_text) < size:
                continue
            for index in range(0, len(cjk_text) - size + 1):
                terms.add(cjk_text[index : index + size])
    return sorted(terms, key=lambda item: (-len(item), item))


def score_article(query: str, article: WikiArticle, chunks: list[str]) -> SearchHit | None:
    terms = extract_query_terms(query)
    if not terms:
        return None
    title = article.title.lower()
    content = article.content_md.lower()
    score = 0.0
    for term in terms:
        if term in title:
            score += 5 + len(term) * 0.2
        score += min(content.count(term), 5) * max(1, min(len(term), 4) / 2)
    if score <= 0:
        return None
    snippet = best_snippet(terms, chunks or [article.summary, article.content_md])
    return SearchHit(article=article, score=score + article.hit_count * 0.1, snippet=snippet)


def best_snippet(terms: list[str], chunks: list[str]) -> str:
    best = ""
    best_score = -1
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(lower.count(term) for term in terms)
        if score > best_score:
            best = chunk
            best_score = score
    return best.strip().replace("\n", " ")[:260]
