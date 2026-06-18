import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_ai_core", sys.modules[__name__])

from . import service as _service_module
from .metadata import __plugin_meta__ as __plugin_meta__
from .models import init_db

sys.modules.setdefault("nonebot_plugin_ai_core.service", _service_module)

AICoreService = _service_module.AICoreService
get_ai_core = _service_module.get_ai_core

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

if "nonebot_plugin_qguard.registry" in sys.modules:
    try:
        from .qguard_registry import register_with_qguard as _register_with_qguard

        _register_with_qguard()
    except Exception:
        pass

__all__ = ["AICoreService", "get_ai_core"]
