from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Rule(TimestampMixin, Base):
    __tablename__ = "rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    score_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mute_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delete_message: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
