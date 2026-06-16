import json
from datetime import datetime, timedelta

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from nonebot_plugin_qguard.config import Config
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.models.message_cache import MessageCache
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo


class MessageCacheService:
    def __init__(self) -> None:
        self.config = Config.parse_obj(get_driver().config.dict())

    async def cache_group_message(self, event: GroupMessageEvent) -> None:
        if not self.config.qguard_enable_message_cache:
            return
        image_count = sum(1 for segment in event.message if segment.type == "image")
        at_count = sum(1 for segment in event.message if segment.type == "at")
        plain_text = event.get_plaintext()
        link_count = plain_text.count("http://") + plain_text.count("https://")
        item = MessageCache(
            message_id=event.message_id,
            group_id=event.group_id,
            user_id=event.user_id,
            plain_text=plain_text,
            raw_message_json=json.dumps([segment.dict() for segment in event.message], ensure_ascii=False),
            image_count=image_count,
            at_count=at_count,
            link_count=link_count,
            expires_at=datetime.utcnow() + timedelta(days=self.config.qguard_message_cache_days),
        )
        async with get_session() as session:
            await MessageCacheRepo(session).upsert(item)
            await session.commit()
