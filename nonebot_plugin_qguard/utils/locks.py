import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta


_locks: defaultdict[tuple[int, int], asyncio.Lock] = defaultdict(asyncio.Lock)
_ignore_until: dict[tuple[int, int], datetime] = {}


def get_member_lock(group_id: int, user_id: int) -> asyncio.Lock:
    return _locks[(group_id, user_id)]


def mark_plugin_fixed(group_id: int, user_id: int, seconds: int) -> None:
    _ignore_until[(group_id, user_id)] = datetime.now(UTC) + timedelta(seconds=seconds)


def should_ignore_card_event(group_id: int, user_id: int) -> bool:
    until = _ignore_until.get((group_id, user_id))
    return until is not None and until > datetime.now(UTC)
