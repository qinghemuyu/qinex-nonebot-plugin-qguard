from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MemberCleanupNotice(TimestampMixin, Base):
    __tablename__ = "member_cleanup_notice"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_member_cleanup_notice_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reminded_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pending_cleanup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pending_cleanup_inactive_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
