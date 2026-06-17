import os

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    group_wiki_db_url: str = "sqlite+aiosqlite:///./data/group_wiki.db"
    group_wiki_enable_ai: bool = True
    group_wiki_default_scope: str = "global"
    group_wiki_import_dir: str = "./知识库"
    group_wiki_max_article_length: int = 20000
    group_wiki_chunk_size: int = 800
    group_wiki_chunk_overlap: int = 100
    group_wiki_max_reply_chars: int = 1200
    group_wiki_software_name: str = "QInEX"


def load_config() -> Config:
    try:
        from nonebot import get_driver

        raw_config = get_driver().config
        data = raw_config.model_dump() if hasattr(raw_config, "model_dump") else raw_config.dict()
    except ValueError:
        data = {}
    for field_name in Config.model_fields:
        env_name = field_name.upper()
        if env_name in os.environ:
            data[field_name] = os.environ[env_name]
    return Config.model_validate(data)
