import asyncio

import nonebot


nonebot.init(driver="~none")

from nonebot_plugin_qguard.models.base import init_db

asyncio.run(init_db())
