from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ai_core_provider: str = "deepseek"
    ai_core_base_url: str = "https://api.deepseek.com"
    ai_core_api_key: str = ""
    ai_core_model: str = "deepseek-chat"
    ai_core_timeout_seconds: int = 45
    ai_core_max_tokens: int = 2048
    ai_core_temperature: float = 0.2
    ai_core_enable_cache: bool = True
    ai_core_cache_ttl_seconds: int = 86400
    ai_core_daily_limit_per_user: int = 30
    ai_core_daily_limit_per_group: int = 300
    ai_core_global_daily_limit: int = 5000
    ai_core_enable_json_repair: bool = True
    ai_core_enable_content_mask: bool = True
    ai_core_log_prompt: bool = False
    ai_core_log_response: bool = False
    ai_core_db_url: str = "sqlite+aiosqlite:///./data/ai_core.db"
    ai_core_super_admins: set[int] = Field(default_factory=lambda: {1348984838})

    # Lets this plugin reuse the existing QGuard owner config when both are installed.
    qguard_super_admins: set[int] = Field(default_factory=set)


def load_config() -> Config:
    try:
        from nonebot import get_driver

        raw_config = get_driver().config
        data = raw_config.model_dump() if hasattr(raw_config, "model_dump") else raw_config.dict()
    except ValueError:
        data = {}

    config = Config.model_validate(data)
    if config.qguard_super_admins:
        config.ai_core_super_admins.update(config.qguard_super_admins)
    return config
