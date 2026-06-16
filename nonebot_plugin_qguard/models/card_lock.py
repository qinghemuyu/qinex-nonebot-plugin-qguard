from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class CardLock(TimestampMixin, Base):
    __tablename__ = "card_lock"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_card_lock_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    locked_card: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_card: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_fixed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_fixed_by_plugin_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
