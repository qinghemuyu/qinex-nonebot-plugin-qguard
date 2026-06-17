from datetime import datetime, timedelta

from nonebot_plugin_ai_core.models import AICache
from nonebot_plugin_ai_core.repositories.cache_repo import AICacheRepo


def build_cache_item(cache_key: str, purpose: str, input_hash: str, response_text: str, ttl_seconds: int) -> AICache:
    return AICache(
        cache_key=cache_key,
        purpose=purpose,
        input_hash=input_hash,
        response_text=response_text,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
    )


__all__ = ["AICacheRepo", "build_cache_item"]
