from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    log_doctor_db_url: str = "sqlite+aiosqlite:///./data/log_doctor.db"
    log_doctor_enable_ai: bool = True
    log_doctor_max_input_chars: int = 12000
    log_doctor_max_reply_chars: int = 1200
    log_doctor_rule_confidence_threshold: float = 0.85


def load_config() -> Config:
    try:
        from nonebot import get_driver

        raw_config = get_driver().config
        data = raw_config.model_dump() if hasattr(raw_config, "model_dump") else raw_config.dict()
    except ValueError:
        data = {}
    return Config.model_validate(data)
