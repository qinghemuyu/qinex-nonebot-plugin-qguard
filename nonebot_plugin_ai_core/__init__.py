import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_ai_core", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .models import init_db
from .service import AICoreService, get_ai_core

try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:

    @driver.on_startup
    async def _init_ai_core() -> None:
        await init_db()

from .commands import status as status  # noqa: E402,F401
from .commands import test_call as test_call  # noqa: E402,F401

__all__ = ["AICoreService", "get_ai_core"]
