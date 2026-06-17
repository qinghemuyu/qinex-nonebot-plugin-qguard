import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 2,
    delay_seconds: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except exceptions as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            await asyncio.sleep(delay_seconds)
    assert last_error is not None
    raise last_error
