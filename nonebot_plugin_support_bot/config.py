import json
import os

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    support_bot_db_url: str = "sqlite+aiosqlite:///./data/support_bot.db"
    support_bot_enabled: bool = True
    support_bot_trigger_mode: str = "command"
    support_bot_enable_smart_listen: bool = False
    support_bot_min_intent_confidence: float = 0.78
    support_bot_session_ttl_seconds: int = 1800
    support_bot_conversation_ttl_seconds: int = 180
    support_bot_max_reply_length: int = 1200
    support_bot_software_name: str = "QInEX"
    support_bot_admins: list[int] = [1348984838]
    support_bot_harassment_enabled: bool = True
    support_bot_harassment_window_seconds: int = 300
    support_bot_harassment_warn_threshold: int = 3
    support_bot_harassment_score_threshold: int = 5
    support_bot_harassment_score_cooldown_seconds: int = 60
    support_bot_harassment_score_delta: int = 1
    support_bot_harassment_max_score_delta: int = 3


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
            value = os.environ[env_name]
            if field_name == "support_bot_admins":
                data[field_name] = _parse_int_list(value)
            else:
                data[field_name] = value
    return Config.model_validate(data)


def _parse_int_list(value: str) -> list[int]:
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [int(item) for item in parsed]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return [int(item.strip()) for item in value.split(",") if item.strip()]
