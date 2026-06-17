from pathlib import Path

from nonebot_plugin_group_wiki.config import Config, load_config
from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.index_repo import WikiSearchIndexRepo
from nonebot_plugin_group_wiki.repositories.version_repo import WikiArticleVersionRepo
from nonebot_plugin_group_wiki.services.chunk_service import ChunkService
from nonebot_plugin_group_wiki.utils.markdown import category_from_path, summary_from_markdown, title_from_markdown


class ImportService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self.chunk_service = ChunkService(self.config)

    async def import_local_markdown(self, *, author_id: int | None = None) -> tuple[int, int, int]:
        base_dir = self.resolve_import_dir()
        if base_dir is None:
            return 0, 0, 0
        created = 0
        updated = 0
        skipped = 0
        async with get_session() as session:
            article_repo = WikiArticleRepo(session)
            index_repo = WikiSearchIndexRepo(session)
            version_repo = WikiArticleVersionRepo(session)
            for path in sorted(base_dir.glob("*.md")):
                content = path.read_text(encoding="utf-8").strip()
                if not content:
                    skipped += 1
                    continue
                title = title_from_markdown(content, path.stem)
                summary = summary_from_markdown(content)
                category = category_from_path(path)
                article, action = await article_repo.upsert_imported(
                    source_ref_id=path.name,
                    title=title,
                    summary=summary,
                    content_md=content[: self.config.group_wiki_max_article_length],
                    category=category,
                    author_id=author_id,
                )
                if action == "created":
                    created += 1
                elif action == "updated":
                    updated += 1
                else:
                    skipped += 1
                    continue
                await version_repo.create_snapshot(article, author_id, "import")
                await index_repo.replace_chunks(
                    article.id,
                    self.chunk_service.build_chunks(article.title, article.summary, article.content_md),
                )
            await session.commit()
        return created, updated, skipped

    def resolve_import_dir(self) -> Path | None:
        candidates = [
            Path(self.config.group_wiki_import_dir),
            Path.cwd() / "知识库",
            Path(__file__).resolve().parents[2] / "知识库",
            Path(__file__).resolve().parents[3] / "知识库",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None
