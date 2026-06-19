import hashlib
import hmac

from nonebot_plugin_qlicense.commands._common import parse_license_command
from nonebot_plugin_qlicense.services.license_client import sign_internal_headers
from nonebot_plugin_qlicense.services.license_service import (
    MAC_SOURCE_TIP,
    extract_mac,
    extract_qq,
    format_account_status,
    format_bind_result,
    parse_quota_args,
)


def test_qlicense_command_parser() -> None:
    assert parse_license_command("/激活 S3 AABBCCDDEEFF") == ("/激活", ["S3"], "AABBCCDDEEFF")
    assert parse_license_command("/激活 状态") == ("/激活", ["状态"], "")
    assert parse_license_command("/授权 配额 1348984838 2") == ("/授权", ["配额"], "1348984838 2")
    assert parse_license_command("/客服 状态") is None


def test_qlicense_hmac_signature() -> None:
    body = b'{"mac":"AABBCCDDEEFF","qq":"1348984838"}'
    headers = sign_internal_headers(
        "POST",
        "/internal/bot/s3/bind",
        body,
        bot_id="qinex-nonebot",
        secret="secret",
        timestamp=123456,
        nonce="nonce",
    )
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(["POST", "/internal/bot/s3/bind", "123456", "nonce", body_hash])
    expected = hmac.new(b"secret", canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    assert headers["X-Qinex-Bot-Id"] == "qinex-nonebot"
    assert headers["X-Qinex-Signature"] == expected


def test_qlicense_extractors_and_quota_args() -> None:
    assert extract_qq("QQ:1348984838") == "1348984838"
    assert extract_mac("mac 是 AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"
    assert parse_quota_args("1348984838 3") == ("1348984838", 3)
    assert parse_quota_args("S3 1348984838 3") == ("1348984838", 3)


def test_qlicense_formatters_include_mac_source_tip() -> None:
    bind_text = format_bind_result(
        {
            "already_bound": False,
            "mac": "AA:BB:CC:**:**:FF",
            "used": 1,
            "quota_total": 2,
        }
    )
    status_text = format_account_status(
        {
            "qq": "1348984838",
            "products": [
                {
                    "product": "s3",
                    "used": 1,
                    "quota_total": 2,
                    "remaining": 1,
                    "bindings": [{"mac": "AA:BB:CC:**:**:FF", "status": "active"}],
                }
            ],
        }
    )

    assert "在线激活" in bind_text
    assert MAC_SOURCE_TIP in bind_text
    assert MAC_SOURCE_TIP in status_text
