from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.utils.hash import hash_text
from nonebot_plugin_group_wiki.utils.text_splitter import split_text


class ChunkService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    def build_chunks(self, title: str, summary: str, content: str) -> list[tuple[int, str, str]]:
        raw_chunks = [f"{title}\n{summary}".strip()]
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
