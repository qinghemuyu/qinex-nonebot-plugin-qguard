import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_qfun", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .models import init_db

try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:

    @driver.on_startup
    async def _init_qfun() -> None:
        await init_db()


from .commands import root as root  # noqa: E402,F401
from .scheduler import wordcloud_jobs as wordcloud_jobs  # noqa: E402,F401

if "nonebot_plugin_qguard.registry" in sys.modules:
    try:
        from .qguard_registry import register_with_qguard as _register_with_qguard

        _register_with_qguard()
    except Exception:
        pass
