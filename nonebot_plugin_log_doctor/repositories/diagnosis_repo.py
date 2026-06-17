from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_log_doctor.models import DiagnosisRecord


class DiagnosisRecordRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, item: DiagnosisRecord) -> DiagnosisRecord:
        self.session.add(item)
        await self.session.flush()
        item.record_no = f"D{datetime.utcnow():%Y%m%d}{item.id:04d}"
        await self.session.flush()
        return item

    async def latest(self, group_id: int | None = None, limit: int = 5) -> list[DiagnosisRecord]:
        stmt = select(DiagnosisRecord).order_by(DiagnosisRecord.id.desc()).limit(limit)
        if group_id is not None:
            stmt = stmt.where(DiagnosisRecord.group_id == group_id)
        result = await self.session.scalars(stmt)
        return list(result)
