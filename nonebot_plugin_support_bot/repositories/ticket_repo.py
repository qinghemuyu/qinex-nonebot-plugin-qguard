from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import Ticket


class TicketRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.flush()
        ticket.ticket_no = f"T{datetime.utcnow():%Y%m%d}{ticket.id:04d}"
        await self.session.flush()
        return ticket

    async def get_by_no(self, ticket_no: str) -> Ticket | None:
        result = await self.session.scalars(
            select(Ticket).where(Ticket.ticket_no == ticket_no.upper())
        )
        return result.one_or_none()

    async def list_group(self, group_id: int, limit: int = 10) -> list[Ticket]:
        result = await self.session.scalars(
            select(Ticket)
            .where(Ticket.group_id == group_id)
            .order_by(Ticket.id.desc())
            .limit(limit)
        )
        return list(result)

    async def list_user(self, group_id: int, user_id: int, limit: int = 10) -> list[Ticket]:
        result = await self.session.scalars(
            select(Ticket)
            .where(Ticket.group_id == group_id, Ticket.user_id == user_id)
            .order_by(Ticket.id.desc())
            .limit(limit)
        )
        return list(result)

    async def assign(self, ticket: Ticket, assignee_id: int) -> Ticket:
        ticket.assignee_id = assignee_id
        ticket.status = "processing"
        ticket.updated_at = datetime.utcnow()
        await self.session.flush()
        return ticket

    async def set_status(self, ticket: Ticket, status: str) -> Ticket:
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        ticket.closed_at = datetime.utcnow() if status in {"resolved", "closed"} else None
        await self.session.flush()
        return ticket
