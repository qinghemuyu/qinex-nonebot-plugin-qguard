from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import Config, load_config


def _load_config() -> Config:
    try:
        return load_config()
    except ValueError:
        return Config()


plugin_config = _load_config()
engine = create_async_engine(plugin_config.support_bot_db_url, future=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class SupportGroupConfig(Base):
    __tablename__ = "support_group_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_mode: Mapped[str] = mapped_column(String(32), default="command", nullable=False)
    smart_listen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SupportSession(Base):
    __tablename__ = "support_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    group_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(64), default="idle", index=True, nullable=False)
    intent: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Ticket(Base):
    __tablename__ = "support_ticket"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="", nullable=False)
    group_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), default="unknown", index=True, nullable=False)
    product: Mapped[str] = mapped_column(String(128), default="QInEX", nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    related_diagnosis_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    related_wiki_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TicketMessage(Base):
    __tablename__ = "support_ticket_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sender_role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attachments_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    if plugin_config.support_bot_db_url.startswith("sqlite"):
        db_path = plugin_config.support_bot_db_url.rsplit("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
