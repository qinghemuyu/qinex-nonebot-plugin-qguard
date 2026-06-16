from sqlalchemy import BigInteger, Boolean, Integer
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
    card_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group_name_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anonymous_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_mute_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    card_lock_patrol_interval_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
