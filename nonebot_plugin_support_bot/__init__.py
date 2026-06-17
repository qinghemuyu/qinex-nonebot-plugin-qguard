import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_support_bot", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .models import init_db
from .services.support_service import SupportBotService

try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:

    @driver.on_startup
    async def _init_support_bot() -> None:
        await init_db()

from .commands import root as root  # noqa: E402,F401

__all__ = ["SupportBotService"]
