import json
import time
from datetime import date, datetime

from pydantic import BaseModel

from .cache.key import build_cache_key, hash_text
from .cache.store import build_cache_item
from .client.base import AIClientResponse, BaseAIClient
from .client.ollama import OllamaClient
from .client.openai_compatible import OpenAICompatibleClient
from .config import Config, load_config
from .exceptions import AIResponseParseError, AIRateLimitExceeded
from .models import AIUsageLog, get_session
from .repositories.cache_repo import AICacheRepo
from .repositories.rate_limit_repo import AIRateLimitRepo
from .repositories.usage_repo import AIUsageLogRepo
from .safety.content_filter import sanitize_messages
from .safety.rate_limit import get_rate_limit_scopes
from .utils.json_repair import parse_model_from_text
from .utils.retry import async_retry
from .utils.token_estimator import estimate_tokens


class AICoreService:
    def __init__(self, config: Config | None = None, client: BaseAIClient | None = None) -> None:
        self.config = config or load_config()
        self.client = client or self._create_client()

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        user_id: int | None = None,
        group_id: int | None = None,
        purpose: str = "general",
    ) -> str:
        sanitized_messages = sanitize_messages(messages, enable_mask=self.config.ai_core_enable_content_mask)
        temperature = self.config.ai_core_temperature if temperature is None else temperature
        max_tokens = self.config.ai_core_max_tokens if max_tokens is None else max_tokens
        cache_key, input_hash = build_cache_key(
            provider=self.config.ai_core_provider,
            model=self.config.ai_core_model,
            purpose=purpose,
            messages=sanitized_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if self.config.ai_core_enable_cache:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return cached

        await self._enforce_rate_limit(user_id=user_id, group_id=group_id)
        start = time.perf_counter()
        prompt_text = json.dumps(sanitized_messages, ensure_ascii=False, sort_keys=True)
        try:
            result = await async_retry(
                lambda: self.client.chat(sanitized_messages, temperature=temperature, max_tokens=max_tokens),
                attempts=2,
            )
        except Exception as exc:
            await self._record_usage(
                purpose=purpose,
                user_id=user_id,
                group_id=group_id,
                success=False,
                error_message=str(exc),
                latency_ms=self._latency_ms(start),
                prompt_text=prompt_text,
                response_text="",
                prompt_tokens=estimate_tokens(prompt_text),
                completion_tokens=0,
                total_tokens=estimate_tokens(prompt_text),
            )
            raise

        await self._record_usage(
            purpose=purpose,
            user_id=user_id,
            group_id=group_id,
            success=True,
            error_message="",
            latency_ms=self._latency_ms(start),
            prompt_text=prompt_text,
            response_text=result.content,
            prompt_tokens=result.prompt_tokens or estimate_tokens(prompt_text),
            completion_tokens=result.completion_tokens or estimate_tokens(result.content),
            total_tokens=result.total_tokens or (estimate_tokens(prompt_text) + estimate_tokens(result.content)),
        )
        if self.config.ai_core_enable_cache:
            await self._set_cached(cache_key, purpose, input_hash, result.content)
        return result.content

    async def classify(
        self,
        text: str,
        labels: list[str],
        *,
        instruction: str = "",
        user_id: int | None = None,
        group_id: int | None = None,
    ) -> str:
        if not labels:
            raise ValueError("labels 不能为空。")
        label_text = " / ".join(labels)
        content = await self.chat(
            [
                {
                    "role": "system",
                    "content": f"你是分类器，只能返回以下标签之一：{label_text}。不要解释。",
                },
                {"role": "user", "content": f"{instruction}\n\n{text}".strip()},
            ],
            user_id=user_id,
            group_id=group_id,
            purpose="classify",
            max_tokens=64,
            temperature=0,
        )
        normalized = content.strip()
        if normalized in labels:
            return normalized
        for label in labels:
            if label in normalized:
                return label
        return labels[0]

    async def extract_json(
        self,
        messages: list[dict],
        schema_model: type[BaseModel],
        *,
        user_id: int | None = None,
        group_id: int | None = None,
        purpose: str = "extract_json",
    ) -> BaseModel:
        schema = schema_model.model_json_schema()
        system_message = {
            "role": "system",
            "content": (
                "你必须输出严格 JSON，不要输出 Markdown，不要解释。"
                "JSON 必须符合这个 schema："
                f"{json.dumps(schema, ensure_ascii=False)}"
            ),
        }
        raw = await self.chat(
            [system_message, *messages],
            user_id=user_id,
            group_id=group_id,
            purpose=purpose,
            temperature=0,
        )
        try:
            return parse_model_from_text(raw, schema_model)
        except AIResponseParseError:
            if not self.config.ai_core_enable_json_repair:
                raise
        repaired = await self.chat(
            [
                system_message,
                {"role": "user", "content": f"修复下面内容为严格 JSON：\n{raw}"},
            ],
            user_id=user_id,
            group_id=group_id,
            purpose=f"{purpose}:repair",
            temperature=0,
        )
        return parse_model_from_text(repaired, schema_model)

    async def summarize(
        self,
        text: str,
        *,
        instruction: str = "",
        max_tokens: int = 1024,
        user_id: int | None = None,
        group_id: int | None = None,
    ) -> str:
        return await self.chat(
            [
                {"role": "system", "content": "你是摘要助手，输出简洁、准确、保留关键事实。"},
                {"role": "user", "content": f"{instruction}\n\n{text}".strip()},
            ],
            user_id=user_id,
            group_id=group_id,
            purpose="summarize",
            max_tokens=max_tokens,
        )

    async def usage_summary(self) -> dict[str, int]:
        async with get_session() as session:
            return await AIUsageLogRepo(session).today_summary(date.today())

    def _create_client(self) -> BaseAIClient:
        if self.config.ai_core_provider.lower() == "ollama":
            return OllamaClient(self.config)
        return OpenAICompatibleClient(self.config)

    async def _get_cached(self, cache_key: str) -> str | None:
        async with get_session() as session:
            cached = await AICacheRepo(session).get_valid(cache_key)
            return None if cached is None else cached.response_text

    async def _set_cached(self, cache_key: str, purpose: str, input_hash: str, response_text: str) -> None:
        async with get_session() as session:
            item = build_cache_item(
                cache_key,
                purpose,
                input_hash,
                response_text,
                self.config.ai_core_cache_ttl_seconds,
            )
            await AICacheRepo(session).upsert(item)
            await session.commit()

    async def _enforce_rate_limit(self, *, user_id: int | None, group_id: int | None) -> None:
        scopes = get_rate_limit_scopes(self.config, user_id=user_id, group_id=group_id)
        async with get_session() as session:
            repo = AIRateLimitRepo(session)
            today = date.today()
            for scope in scopes:
                if scope.limit <= 0:
                    continue
                current = await repo.get_count(scope.scope_type, scope.scope_id, today)
                if current >= scope.limit:
                    raise AIRateLimitExceeded(f"AI 调用已达到今日限流：{scope.scope_type}={scope.scope_id}，上限 {scope.limit} 次。")
            for scope in scopes:
                if scope.limit > 0:
                    await repo.increment(scope.scope_type, scope.scope_id, today)
            await session.commit()

    async def _record_usage(
        self,
        *,
        purpose: str,
        user_id: int | None,
        group_id: int | None,
        success: bool,
        error_message: str,
        latency_ms: int,
        prompt_text: str,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        async with get_session() as session:
            await AIUsageLogRepo(session).create(
                AIUsageLog(
                    provider=self.config.ai_core_provider,
                    model=self.config.ai_core_model,
                    purpose=purpose,
                    group_id=group_id,
                    user_id=user_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    success=success,
                    error_message=error_message[:2000],
                    latency_ms=latency_ms,
                    prompt_hash=hash_text(prompt_text),
                    response_hash=hash_text(response_text),
                    prompt_text=prompt_text if self.config.ai_core_log_prompt else "",
                    response_text=response_text if self.config.ai_core_log_response else "",
                    created_at=datetime.now(),
                )
            )
            await session.commit()

    @staticmethod
    def _latency_ms(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)


_ai_core: AICoreService | None = None


def get_ai_core() -> AICoreService:
    global _ai_core
    if _ai_core is None:
        _ai_core = AICoreService()
    return _ai_core
