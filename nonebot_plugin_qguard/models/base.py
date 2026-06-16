from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from nonebot import get_driver
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from nonebot_plugin_qguard.config import Config


def _load_config() -> Config:
    try:
        return Config.parse_obj(get_driver().config.dict())
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

    from . import audit_log, blacklist, card_lock, group_config, member_profile, message_cache, rule, whitelist  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
