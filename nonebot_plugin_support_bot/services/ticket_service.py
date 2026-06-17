import json

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import Ticket, get_session
from nonebot_plugin_support_bot.repositories.ticket_message_repo import TicketMessageRepo
from nonebot_plugin_support_bot.repositories.ticket_repo import TicketRepo
from nonebot_plugin_support_bot.services.schemas import SupportIntent


class TicketService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    async def create_ticket(
        self,
        *,
        description: str,
        group_id: int | None,
        user_id: int,
        intent: SupportIntent | None = None,
        related_diagnosis_id: str = "",
        related_wiki_ids: list[str] | None = None,
        sender_role: str = "user",
    ) -> Ticket:
        intent = intent or SupportIntent(issue_type="unknown")
        summary = self._build_summary(description)
        async with get_session() as session:
            ticket_repo = TicketRepo(session)
            message_repo = TicketMessageRepo(session)
            ticket = await ticket_repo.create(
                Ticket(
                    group_id=int(group_id or 0),
                    user_id=user_id,
                    status="open",
                    priority=self._priority_from_intent(intent),
                    issue_type=intent.issue_type,
                    product=intent.product or self.config.support_bot_software_name,
                    summary=summary,
                    description=description.strip(),
                    related_diagnosis_id=related_diagnosis_id,
                    related_wiki_ids_json=json.dumps(related_wiki_ids or [], ensure_ascii=False),
                )
            )
            await message_repo.create(
                ticket_id=ticket.id,
                sender_id=user_id,
                sender_role=sender_role,
                content=description.strip(),
            )
            await session.commit()
            return ticket

    async def get_ticket(self, ticket_no: str) -> tuple[Ticket | None, list] | tuple[None, list]:
        async with get_session() as session:
            repo = TicketRepo(session)
            ticket = await repo.get_by_no(ticket_no)
            if ticket is None:
                return None, []
            messages = await TicketMessageRepo(session).list_by_ticket(ticket.id)
            return ticket, messages

    async def list_group_tickets(self, group_id: int, limit: int = 10) -> list[Ticket]:
        async with get_session() as session:
            return await TicketRepo(session).list_group(group_id, limit=limit)

    async def list_user_tickets(self, group_id: int, user_id: int, limit: int = 10) -> list[Ticket]:
        async with get_session() as session:
            return await TicketRepo(session).list_user(group_id, user_id, limit=limit)

    async def assign_ticket(self, ticket_no: str, assignee_id: int) -> Ticket | None:
        async with get_session() as session:
            repo = TicketRepo(session)
            ticket = await repo.get_by_no(ticket_no)
            if ticket is None:
                return None
            await repo.assign(ticket, assignee_id)
            await TicketMessageRepo(session).create(
                ticket_id=ticket.id,
                sender_id=assignee_id,
                sender_role="admin",
                content="接单处理",
            )
            await session.commit()
            return ticket

    async def add_note(self, ticket_no: str, *, sender_id: int, sender_role: str, content: str) -> Ticket | None:
        async with get_session() as session:
            repo = TicketRepo(session)
            ticket = await repo.get_by_no(ticket_no)
            if ticket is None:
                return None
            await TicketMessageRepo(session).create(
                ticket_id=ticket.id,
                sender_id=sender_id,
                sender_role=sender_role,
                content=content.strip(),
            )
            await session.commit()
            return ticket

    async def set_status(self, ticket_no: str, status: str, *, operator_id: int) -> Ticket | None:
        async with get_session() as session:
            repo = TicketRepo(session)
            ticket = await repo.get_by_no(ticket_no)
            if ticket is None:
                return None
            await repo.set_status(ticket, status)
            await TicketMessageRepo(session).create(
                ticket_id=ticket.id,
                sender_id=operator_id,
                sender_role="admin",
                content=f"状态变更为 {status}",
            )
            await session.commit()
            return ticket

    @staticmethod
    def _build_summary(description: str) -> str:
        text = " ".join(description.strip().split())
        if not text:
            return "未填写问题描述"
        return text[:80]

    @staticmethod
    def _priority_from_intent(intent: SupportIntent) -> str:
        if intent.urgency in {"high", "urgent"}:
            return intent.urgency
        if intent.issue_type in {"license_problem", "payment_order", "launch_failed"}:
            return "high"
        return "normal"
