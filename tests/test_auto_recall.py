from types import SimpleNamespace

from nonebot_plugin_qguard.config import Config
from nonebot_plugin_qguard.services.auto_recall_service import (
    NON_ADMIN_MAX_AUTO_DELETE_SECONDS,
    clamp_auto_delete_seconds,
    extract_message_id,
)


def test_default_auto_delete_reply_seconds() -> None:
    assert Config().qguard_default_auto_delete_reply_seconds == 90


def test_extract_message_id() -> None:
    assert extract_message_id({"message_id": "123"}) == 123
    assert extract_message_id(SimpleNamespace(message_id=456)) == 456
    assert extract_message_id({"message_id": "bad"}) is None
    assert extract_message_id({}) is None


def test_clamp_auto_delete_seconds() -> None:
    assert clamp_auto_delete_seconds(0, "member") == 0
    assert clamp_auto_delete_seconds(150, "member") == NON_ADMIN_MAX_AUTO_DELETE_SECONDS
    assert clamp_auto_delete_seconds(150, None) == NON_ADMIN_MAX_AUTO_DELETE_SECONDS
    assert clamp_auto_delete_seconds(150, "admin") == 150
    assert clamp_auto_delete_seconds(150, "owner") == 150
