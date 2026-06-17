from nonebot_plugin_ai_core.config import Config
from nonebot_plugin_ai_core.exceptions import AIClientError

from .base import AIClientResponse


class OpenAICompatibleClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
    ) -> AIClientResponse:
        try:
            import httpx
        except ImportError as exc:
            raise AIClientError("缺少依赖 httpx，请先安装 nonebot-plugin-ai-core 的依赖。") from exc

        if not self.config.ai_core_api_key:
            raise AIClientError("AI_CORE_API_KEY 未配置。")

        payload = {
            "model": self.config.ai_core_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.config.ai_core_api_key}"}
        timeout = httpx.Timeout(self.config.ai_core_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(self._chat_url(), json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise AIClientError(str(exc)) from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIClientError("AI 响应格式不符合 OpenAI-compatible Chat Completions。") from exc

        usage = data.get("usage") or {}
        return AIClientResponse(
            content=content or "",
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
            raw=data,
        )

    def _chat_url(self) -> str:
        base_url = self.config.ai_core_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"
