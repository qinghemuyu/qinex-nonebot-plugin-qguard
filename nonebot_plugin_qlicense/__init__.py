import sys

sys.modules.setdefault("nonebot_plugin_qlicense", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .commands import root as root  # noqa: E402,F401

if "nonebot_plugin_qguard.registry" in sys.modules:
    try:
        from .qguard_registry import register_with_qguard as _register_with_qguard

        _register_with_qguard()
    except Exception:
        pass
