import sys

from nonebot import get_driver

sys.modules.setdefault("nonebot_plugin_qguard", sys.modules[__name__])

from .metadata import __plugin_meta__ as __plugin_meta__
from .models.base import init_db

driver = get_driver()


@driver.on_startup
async def _init_qguard() -> None:
    await init_db()


from .commands import audit as audit  # noqa: E402,F401
from .commands import blacklist as blacklist  # noqa: E402,F401
from .commands import card as card  # noqa: E402,F401
from .commands import card_lock as card_lock  # noqa: E402,F401
from .commands import group_setting as group_setting  # noqa: E402,F401
from .commands import inactive_cleanup as inactive_cleanup  # noqa: E402,F401
from .commands import join_review as join_review  # noqa: E402,F401
from .commands import member_role as member_role  # noqa: E402,F401
from .commands import message_query as message_query  # noqa: E402,F401
from .commands import moderation as moderation  # noqa: E402,F401
from .commands import newbie as newbie  # noqa: E402,F401
from .commands import punish as punish  # noqa: E402,F401
from .commands import rule as rule  # noqa: E402,F401
from .commands import root as root  # noqa: E402,F401
from .commands import score as score  # noqa: E402,F401
from .commands import whitelist as whitelist  # noqa: E402,F401
from .handlers import message_handler as message_handler  # noqa: E402,F401
from .handlers import notice_handler as notice_handler  # noqa: E402,F401
from .handlers import request_handler as request_handler  # noqa: E402,F401
from .scheduler import cleanup_jobs as cleanup_jobs  # noqa: E402,F401
from .scheduler import patrol_jobs as patrol_jobs  # noqa: E402,F401
