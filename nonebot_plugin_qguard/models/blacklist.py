from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Blacklist(TimestampMixin, Base):
    __tablename__ = "blacklist"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_blacklist_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
