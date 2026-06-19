from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint
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


class SupportNoAnswer(Base):
    __tablename__ = "support_no_answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, default="", nullable=False)
    group_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(String(128), default="no_knowledge", nullable=False)
    notified_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SupportIssueCluster(Base):
    __tablename__ = "support_issue_cluster"
    __table_args__ = (UniqueConstraint("cluster_key", name="uq_support_issue_cluster_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    skill: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    example_question: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_question: Mapped[str] = mapped_column(Text, default="", nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_answer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unresolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_group_id: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_user_id: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_record_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SupportHarassmentMemory(Base):
    __tablename__ = "support_harassment_memory"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_support_harassment_group_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    anger_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_strikes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_punish_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reason: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    last_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_score_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


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
