import hashlib
import json


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_cache_key(
    *,
    provider: str,
    model: str,
    purpose: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[str, str]:
    raw = json.dumps(
        {
            "provider": provider,
            "model": model,
            "purpose": purpose,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    input_hash = hash_text(raw)
    return hash_text(f"{purpose}:{provider}:{model}:{input_hash}"), input_hash
