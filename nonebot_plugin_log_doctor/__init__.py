import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_log_doctor", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .models import init_db
from .services.diagnose_service import LogDoctorService

try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:

    @driver.on_startup
    async def _init_log_doctor() -> None:
        await init_db()

__all__ = ["LogDoctorService"]
