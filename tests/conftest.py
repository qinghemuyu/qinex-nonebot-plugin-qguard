import asyncio
import os
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import nonebot


os.environ.setdefault(
    "GROUP_WIKI_DB_URL",
    f"sqlite+aiosqlite:///{Path(gettempdir()).as_posix()}/group_wiki_test_{uuid4().hex}.db",
)
os.environ.setdefault(
    "SUPPORT_BOT_DB_URL",
    f"sqlite+aiosqlite:///{Path(gettempdir()).as_posix()}/support_bot_test_{uuid4().hex}.db",
)
os.environ.setdefault(
    "QFUN_DB_URL",
    f"sqlite+aiosqlite:///{Path(gettempdir()).as_posix()}/qfun_test_{uuid4().hex}.db",
)

nonebot.init(driver="~none")

from nonebot_plugin_qguard.models.base import init_db

asyncio.run(init_db())
