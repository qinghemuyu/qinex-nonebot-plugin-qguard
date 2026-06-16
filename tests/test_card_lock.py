from nonebot_plugin_qguard.utils.locks import get_member_lock, mark_plugin_fixed, should_ignore_card_event


def test_member_lock_is_stable() -> None:
    assert get_member_lock(1, 2) is get_member_lock(1, 2)
    assert get_member_lock(1, 2) is not get_member_lock(1, 3)


def test_ignore_window() -> None:
    mark_plugin_fixed(10, 20, 10)
    assert should_ignore_card_event(10, 20)
    assert not should_ignore_card_event(10, 21)
