from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MemberProfile(TimestampMixin, Base):
    __tablename__ = "member_profile"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_member_profile_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trust_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kick_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    join_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    newbie_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
