from __future__ import annotations

import hashlib
import hmac
import json
import time
from secrets import token_hex
from urllib.parse import urlparse

from nonebot_plugin_qlicense.config import Config


class LicenseAPIError(RuntimeError):
    def __init__(self, message: str, *, data=None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.data = data
        self.status_code = status_code


class LicenseClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    async def post(self, path: str, payload: dict) -> dict:
        self._ensure_configured()
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            **sign_internal_headers(
                "POST",
                path,
                body,
                bot_id=self.config.qlicense_bot_id,
                secret=self.config.qlicense_api_secret,
            ),
        }
        url = self.config.qlicense_api_base_url.rstrip("/") + path
        try:
            import httpx
        except ImportError as exc:
            raise LicenseAPIError("未安装 httpx，无法请求授权服务") from exc
        async with httpx.AsyncClient(timeout=self.config.qlicense_timeout_seconds) as client:
            response = await client.post(url, content=body, headers=headers)
        try:
            data = response.json()
        except ValueError as exc:
            raise LicenseAPIError("授权服务返回了非 JSON 响应", status_code=response.status_code) from exc
        if response.status_code >= 400 or int(data.get("code", 1)) != 0:
            raise LicenseAPIError(
                str(data.get("message") or f"授权服务请求失败 HTTP {response.status_code}"),
                data=data.get("data"),
                status_code=response.status_code,
            )
        return data.get("data") or {}

    def _ensure_configured(self) -> None:
        if not self.config.qlicense_api_base_url.strip():
            raise LicenseAPIError("未配置 QLICENSE_API_BASE_URL")
        if not self.config.qlicense_api_secret.strip():
            raise LicenseAPIError("未配置 QLICENSE_API_SECRET")
        if self.config.qlicense_require_secure_transport and not _is_secure_or_loopback(self.config.qlicense_api_base_url):
            raise LicenseAPIError("授权服务地址必须是 HTTPS，或使用 127.0.0.1/localhost 本机回环地址")


def sign_internal_headers(
    method: str,
    path: str,
    body: bytes,
    *,
    bot_id: str,
    secret: str,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp = int(time.time()) if timestamp is None else int(timestamp)
    nonce = nonce or token_hex(16)
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join([method.upper(), path, str(timestamp), nonce, body_hash])
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-Qinex-Bot-Id": bot_id,
        "X-Qinex-Timestamp": str(timestamp),
        "X-Qinex-Nonce": nonce,
        "X-Qinex-Signature": signature,
    }


def _is_secure_or_loopback(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return True
    if parsed.scheme != "http":
        return False
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}
