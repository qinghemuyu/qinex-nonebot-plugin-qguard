from pydantic import BaseModel, Field


class Config(BaseModel):
    qlicense_api_base_url: str = "http://127.0.0.1:5000"
    qlicense_bot_id: str = "qinex-nonebot"
    qlicense_api_secret: str = ""
    qlicense_timeout_seconds: float = 8.0
    qlicense_require_secure_transport: bool = True
    qlicense_super_admins: set[int] = Field(default_factory=lambda: {1348984838})


def load_config() -> Config:
    from nonebot import get_driver

    raw_config = get_driver().config
    data = raw_config.model_dump() if hasattr(raw_config, "model_dump") else raw_config.dict()
    if hasattr(Config, "model_validate"):
        return Config.model_validate(data)
    return Config.parse_obj(data)
