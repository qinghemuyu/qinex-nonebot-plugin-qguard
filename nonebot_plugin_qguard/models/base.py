from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from nonebot import get_driver
from sqlalchemy import DateTime, text
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from nonebot_plugin_qguard.config import Config, load_config


def _load_config() -> Config:
    try:
        return load_config()
    except ValueError:
        return Config()


plugin_config = _load_config()
engine = create_async_engine(plugin_config.qguard_db_url, future=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
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
    if plugin_config.qguard_db_url.startswith("sqlite"):
        db_path = plugin_config.qguard_db_url.rsplit("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    from . import (  # noqa: F401
        ad_keyword,
        audit_log,
        blacklist,
        card_lock,
        group_config,
        member_profile,
        message_cache,
        rule,
        whitelist,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if plugin_config.qguard_db_url.startswith("sqlite"):
            await _migrate_sqlite_schema(conn)


async def _migrate_sqlite_schema(conn: AsyncConnection) -> None:
    await _add_sqlite_column_if_missing(
        conn,
        "card_lock",
        "failure_count",
        "INTEGER NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "card_lock",
        "last_fixed_by_plugin_at",
        "DATETIME NULL",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "message_cache",
        "updated_at",
        "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "anti_ad_enabled",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "anti_spam_enabled",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "newbie_protection_seconds",
        "INTEGER NOT NULL DEFAULT 86400",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "newbie_block_links",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "newbie_block_images",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "auto_delete_reply_seconds",
        "INTEGER NOT NULL DEFAULT 90",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "auto_delete_reply_categories",
        "TEXT NOT NULL DEFAULT 'command'",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "join_review_answer",
        "TEXT NOT NULL DEFAULT ''",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "join_review_reject_reason",
        "TEXT NOT NULL DEFAULT '入群验证未通过。'",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "locked_group_name",
        "TEXT NOT NULL DEFAULT ''",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "anonymous_enabled",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "auto_patrol_enabled",
        "BOOLEAN NOT NULL DEFAULT 0",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "auto_patrol_interval_seconds",
        "INTEGER NOT NULL DEFAULT 1800",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "group_config",
        "last_auto_patrol_at",
        "DATETIME NULL",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "audit_log",
        "updated_at",
        "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "whitelist",
        "updated_at",
        "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    )
    await _add_sqlite_column_if_missing(
        conn,
        "blacklist",
        "updated_at",
        "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    )


async def _add_sqlite_column_if_missing(
    conn: AsyncConnection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    columns = {row[1] for row in result}
    if column_name not in columns:
        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
