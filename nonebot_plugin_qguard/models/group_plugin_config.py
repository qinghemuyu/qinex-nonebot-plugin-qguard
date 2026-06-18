from __future__ import annotations

import json

from sqlalchemy import BigInteger, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class GroupPluginConfig(TimestampMixin, Base):
    __tablename__ = "group_plugin_config"
    __table_args__ = (UniqueConstraint("group_id", "plugin_id", name="uq_group_plugin_config_group_plugin"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    plugin_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    command_enabled_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_override_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    @property
    def permission_overrides(self) -> dict[str, int]:
        if not self.permission_override_json:
            return {}
        try:
            data = json.loads(self.permission_override_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        result: dict[str, int] = {}
        for key, value in data.items():
            try:
                result[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
        return result
