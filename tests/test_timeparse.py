import pytest

from nonebot_plugin_qguard.utils.timeparse import parse_duration


def test_parse_duration_units() -> None:
    assert parse_duration("10s") == 10
    assert parse_duration("10m") == 600
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("0") == 0
    assert parse_duration("永久", permanent_seconds=123) == 123


def test_parse_duration_invalid() -> None:
    with pytest.raises(ValueError):
        parse_duration("abc")
