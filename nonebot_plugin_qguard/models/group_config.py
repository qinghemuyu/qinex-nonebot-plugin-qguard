from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class GroupConfig(TimestampMixin, Base):
    __tablename__ = "group_config"

    group_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    anti_ad_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anti_spam_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    keyword_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_member_protection_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    join_review_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    join_review_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    join_review_reject_reason: Mapped[str] = mapped_column(Text, default="入群验证未通过。", nullable=False)
    card_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group_name_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_group_name: Mapped[str] = mapped_column(Text, default="", nullable=False)
    anonymous_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anonymous_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_mute_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    card_lock_patrol_interval_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    auto_patrol_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_patrol_interval_seconds: Mapped[int] = mapped_column(Integer, default=1800, nullable=False)
    last_auto_patrol_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_cleanup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_cleanup_interval_seconds: Mapped[int] = mapped_column(Integer, default=86400, nullable=False)
    auto_cleanup_reminder_days: Mapped[str] = mapped_column(Text, default="30,60", nullable=False)
    auto_cleanup_kick_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    last_auto_cleanup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    newbie_protection_seconds: Mapped[int] = mapped_column(Integer, default=86400, nullable=False)
    newbie_block_links: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    newbie_block_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_delete_reply_seconds: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    auto_delete_reply_categories: Mapped[str] = mapped_column(Text, default="command", nullable=False)
