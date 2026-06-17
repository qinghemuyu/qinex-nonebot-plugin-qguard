from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.utils.hash import hash_text
from nonebot_plugin_group_wiki.utils.markdown import split_markdown_sections
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


class ChunkService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    def build_chunks(self, title: str, summary: str, content: str) -> list[tuple[int, str, str]]:
        raw_chunks = [f"{title}\n{summary}".strip()]
        sections = split_markdown_sections(content)
        if sections:
            raw_chunks.extend(self._split_sections(sections))
        else:
            raw_chunks.extend(
                split_text(
                    content,
                    chunk_size=self.config.group_wiki_chunk_size,
                    overlap=self.config.group_wiki_chunk_overlap,
                )
            )
        result: list[tuple[int, str, str]] = []
        for index, chunk in enumerate(raw_chunks):
            text = chunk.strip()
            if text:
                result.append((index, text, hash_text(text)))
        return result

    def _split_sections(self, sections: list[str]) -> list[str]:
        chunks: list[str] = []
        limit = self.config.group_wiki_chunk_size
        overlap = self.config.group_wiki_chunk_overlap
        for section in sections:
            if len(section) <= limit:
                chunks.append(section)
                continue
            lines = section.splitlines()
            heading = lines[0] if lines and lines[0].lstrip().startswith("#") else ""
            body = "\n".join(lines[1:]) if heading else section
            for part in split_text(body, chunk_size=limit, overlap=overlap):
                chunks.append(f"{heading}\n{part}".strip() if heading else part)
        return chunks
