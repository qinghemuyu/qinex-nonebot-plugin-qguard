from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.base import plugin_config
from nonebot_plugin_qguard.models.group_config import GroupConfig


class GroupConfigRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int) -> GroupConfig | None:
        return await self.session.get(GroupConfig, group_id)

    async def get_or_create(self, group_id: int) -> GroupConfig:
        config = await self.get(group_id)
        if config is None:
            if plugin_config.qguard_db_url.startswith("sqlite"):
                await self._insert_sqlite_compatible(group_id)
                config = await self.get(group_id)
                if config is None:
                    raise RuntimeError(f"failed to create group_config for group {group_id}")
            else:
                config = GroupConfig(group_id=group_id)
                self.session.add(config)
                await self.session.flush()
        return config

    async def _insert_sqlite_compatible(self, group_id: int) -> None:
        now = datetime.utcnow()
        defaults: dict[str, Any] = {
            "group_id": group_id,
            "enabled": True,
            "auto_moderation_enabled": True,
            "anti_ad_enabled": False,
            "anti_spam_enabled": False,
            "keyword_check_enabled": True,
            "new_member_protection_enabled": False,
            "join_review_enabled": False,
            "join_review_answer": "",
            "join_review_reject_reason": "入群验证未通过。",
            "card_lock_enabled": True,
            "group_name_lock_enabled": False,
            "anonymous_lock_enabled": False,
            "message_cache_enabled": True,
            "default_mute_seconds": 600,
            "card_lock_patrol_interval_seconds": 600,
            "newbie_protection_seconds": 86400,
            "newbie_block_links": True,
            "newbie_block_images": False,
            "auto_delete_reply_seconds": plugin_config.qguard_default_auto_delete_reply_seconds,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.session.execute(text("PRAGMA table_info(group_config)"))
        columns: list[tuple[str, str, bool, bool]] = []
        for row in result:
            name = str(row[1])
            column_type = str(row[2] or "")
            not_null = bool(row[3])
            default_value = row[4]
            pk = bool(row[5])
            if name in defaults or (not_null and default_value is None and not pk):
                columns.append((name, column_type, not_null, pk))

        values = {
            name: defaults.get(name, self._fallback_value(name, column_type))
            for name, column_type, _not_null, _pk in columns
        }
        quoted_columns = ", ".join(f'"{name}"' for name in values)
        placeholders = ", ".join(f":{name}" for name in values)
        await self.session.execute(
            text(f"INSERT INTO group_config ({quoted_columns}) VALUES ({placeholders})"),
            values,
        )
        await self.session.flush()

    @staticmethod
    def _fallback_value(name: str, column_type: str) -> Any:
        normalized = column_type.upper()
        if "BOOL" in normalized:
            return False
        if "INT" in normalized:
            return 0
        if any(token in normalized for token in ("REAL", "FLOA", "DOUB", "NUM")):
            return 0
        if "DATE" in normalized or "TIME" in normalized:
            return datetime.utcnow()
        if name.endswith("_enabled") or name.startswith("enable_") or name.startswith("newbie_block_"):
            return False
        return ""

    async def set_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.enabled = enabled
        await self.session.flush()
        return config

    async def set_card_lock_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.card_lock_enabled = enabled
        await self.session.flush()
        return config

    async def set_auto_delete_reply_seconds(self, group_id: int, seconds: int) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.auto_delete_reply_seconds = seconds
        await self.session.flush()
        return config

    async def set_join_review_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.join_review_enabled = enabled
        await self.session.flush()
        return config

    async def set_join_review_answer(self, group_id: int, answer: str) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.join_review_answer = answer
        await self.session.flush()
        return config

    async def set_join_review_reject_reason(self, group_id: int, reason: str) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.join_review_reject_reason = reason
        await self.session.flush()
        return config

    async def set_new_member_protection_enabled(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.new_member_protection_enabled = enabled
        if enabled:
            config.newbie_block_links = True
        await self.session.flush()
        return config

    async def set_newbie_protection_seconds(self, group_id: int, seconds: int) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.newbie_protection_seconds = seconds
        await self.session.flush()
        return config

    async def set_newbie_block_images(self, group_id: int, enabled: bool) -> GroupConfig:
        config = await self.get_or_create(group_id)
        config.newbie_block_images = enabled
        await self.session.flush()
        return config

    async def list_card_lock_enabled_groups(self) -> list[GroupConfig]:
        result = await self.session.scalars(
            select(GroupConfig).where(GroupConfig.enabled.is_(True), GroupConfig.card_lock_enabled.is_(True))
        )
        return list(result)
