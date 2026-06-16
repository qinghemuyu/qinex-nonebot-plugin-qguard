from pydantic import BaseModel, Field

from .constants import DEFAULT_COMMAND_PREFIX


class Config(BaseModel):
    qguard_db_url: str = "sqlite+aiosqlite:///./data/qguard.db"
    qguard_super_admins: set[int] = Field(default_factory=set)
    qguard_default_enable: bool = True
    qguard_default_mute_seconds: int = 600
    qguard_message_cache_days: int = 7
    qguard_card_lock_patrol_interval_seconds: int = 600
    qguard_auto_patrol_interval_seconds: int = 1800
    qguard_enable_auto_moderation: bool = True
    qguard_enable_message_cache: bool = True
    qguard_command_prefix: str = DEFAULT_COMMAND_PREFIX
