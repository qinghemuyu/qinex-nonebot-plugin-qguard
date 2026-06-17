from dataclasses import dataclass

from nonebot_plugin_ai_core.config import Config


@dataclass(slots=True)
class RateLimitScope:
    scope_type: str
    scope_id: int
    limit: int


def get_rate_limit_scopes(config: Config, *, user_id: int | None, group_id: int | None) -> list[RateLimitScope]:
    scopes = [RateLimitScope("global", 0, config.ai_core_global_daily_limit)]
    if group_id is not None:
        scopes.append(RateLimitScope("group", group_id, config.ai_core_daily_limit_per_group))
    if user_id is not None:
        scopes.append(RateLimitScope("user", user_id, config.ai_core_daily_limit_per_user))
    return scopes
