from pydantic import BaseModel, Field


class Config(BaseModel):
    qfun_db_url: str = "sqlite+aiosqlite:///./data/qfun.db"
    qfun_default_enabled: bool = True
    qfun_wordcloud_default_time: str = "21:30"
    qfun_wordcloud_default_period: str = "今日"
    qfun_wordcloud_top_limit: int = 20
    qfun_wordcloud_message_limit: int = 5000
    qfun_super_admins: set[int] = Field(default_factory=lambda: {1348984838})


def load_config() -> Config:
    from nonebot import get_driver

    raw_config = get_driver().config
    data = raw_config.model_dump() if hasattr(raw_config, "model_dump") else raw_config.dict()
    if hasattr(Config, "model_validate"):
        return Config.model_validate(data)
    return Config.parse_obj(data)
