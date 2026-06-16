from .metadata import __plugin_meta__ as __plugin_meta__

try:
    from nonebot import get_driver

    from .models.base import init_db

    driver = get_driver()
except ValueError:
    driver = None


if driver is not None:

    @driver.on_startup
    async def _init_qguard() -> None:
        await init_db()


    from .commands import audit as audit  # noqa: E402,F401
    from .commands import card as card  # noqa: E402,F401
    from .commands import card_lock as card_lock  # noqa: E402,F401
    from .commands import punish as punish  # noqa: E402,F401
    from .commands import root as root  # noqa: E402,F401
    from .handlers import message_handler as message_handler  # noqa: E402,F401
    from .handlers import notice_handler as notice_handler  # noqa: E402,F401
    from .scheduler import card_lock_jobs as card_lock_jobs  # noqa: E402,F401
    from .scheduler import cleanup_jobs as cleanup_jobs  # noqa: E402,F401
