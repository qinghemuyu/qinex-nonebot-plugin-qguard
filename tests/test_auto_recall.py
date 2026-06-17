from types import SimpleNamespace

from nonebot_plugin_qguard.config import Config
from nonebot_plugin_qguard.services.auto_recall_service import (
    AUTO_RECALL_CHAT,
    AUTO_RECALL_COMMAND,
    NON_ADMIN_MAX_AUTO_DELETE_SECONDS,
    clamp_auto_delete_seconds,
    deserialize_auto_recall_categories,
    extract_message_id,
    format_auto_recall_categories,
    parse_auto_recall_categories,
    serialize_auto_recall_categories,
    should_auto_recall_message,
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


def test_auto_recall_category_parse_and_format() -> None:
    assert parse_auto_recall_categories("指令") == {AUTO_RECALL_COMMAND}
    assert parse_auto_recall_categories("聊天") == {AUTO_RECALL_CHAT}
    assert parse_auto_recall_categories("全部") == {AUTO_RECALL_COMMAND, AUTO_RECALL_CHAT}
    assert parse_auto_recall_categories("关闭") == set()
    assert parse_auto_recall_categories("指令,聊天") == {AUTO_RECALL_COMMAND, AUTO_RECALL_CHAT}
    assert serialize_auto_recall_categories({AUTO_RECALL_CHAT, AUTO_RECALL_COMMAND}) == "command,chat"
    assert deserialize_auto_recall_categories("command,chat") == {AUTO_RECALL_COMMAND, AUTO_RECALL_CHAT}
    assert format_auto_recall_categories({AUTO_RECALL_COMMAND}) == "指令"
    assert format_auto_recall_categories({AUTO_RECALL_CHAT}) == "聊天"


def test_should_auto_recall_message_by_category() -> None:
    assert should_auto_recall_message("command", AUTO_RECALL_COMMAND)
    assert not should_auto_recall_message("command", AUTO_RECALL_CHAT)
    assert should_auto_recall_message("chat", AUTO_RECALL_CHAT)
    assert should_auto_recall_message("command,chat", AUTO_RECALL_CHAT)
    assert not should_auto_recall_message("", AUTO_RECALL_COMMAND)
