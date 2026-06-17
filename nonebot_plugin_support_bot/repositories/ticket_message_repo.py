from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import TicketMessage


class TicketMessageRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        ticket_id: int,
        sender_id: int | None,
        sender_role: str,
        content: str,
    ) -> TicketMessage:
        item = TicketMessage(
            ticket_id=ticket_id,
            sender_id=sender_id,
            sender_role=sender_role,
            content=content,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_by_ticket(self, ticket_id: int, limit: int = 20) -> list[TicketMessage]:
        result = await self.session.scalars(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.id.asc())
            .limit(limit)
        )
        return list(result)
