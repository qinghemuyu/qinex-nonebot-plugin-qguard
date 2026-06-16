from nonebot_plugin_qguard.utils.locks import get_member_lock, mark_plugin_fixed, should_ignore_card_event
from nonebot_plugin_qguard.services.card_lock_service import CardLockService


def test_member_lock_is_stable() -> None:
    assert get_member_lock(1, 2) is get_member_lock(1, 2)
    assert get_member_lock(1, 2) is not get_member_lock(1, 3)


def test_ignore_window() -> None:
    mark_plugin_fixed(10, 20, 10)
    assert should_ignore_card_event(10, 20)
    assert not should_ignore_card_event(10, 21)


class FakeOps:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, bool]] = []

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True):
        self.calls.append((group_id, user_id, no_cache))
        return {"card": "fresh"}


async def test_get_current_card_uses_no_cache() -> None:
    ops = FakeOps()
    card = await CardLockService()._get_current_card(ops, 1, 2)
    assert card == "fresh"
    assert ops.calls == [(1, 2, True)]
