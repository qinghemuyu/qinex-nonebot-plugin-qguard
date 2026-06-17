from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import Config, load_config


def _load_config() -> Config:
    try:
        return load_config()
    except ValueError:
        return Config()


plugin_config = _load_config()
engine = create_async_engine(plugin_config.log_doctor_db_url, future=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="", nullable=False)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="command", nullable=False)
    raw_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text_excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(128), default="unknown", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fix_steps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_ticket_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_wiki_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DiagnosisRule(Base):
    __tablename__ = "diagnosis_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    patterns_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fix_steps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    if plugin_config.log_doctor_db_url.startswith("sqlite"):
        db_path = plugin_config.log_doctor_db_url.rsplit("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
