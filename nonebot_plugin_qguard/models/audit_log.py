from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    target_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    related_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
