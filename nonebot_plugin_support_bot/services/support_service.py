import json

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import get_session
from nonebot_plugin_support_bot.repositories.group_config_repo import SupportGroupConfigRepo
from nonebot_plugin_support_bot.repositories.session_repo import SupportSessionRepo
from nonebot_plugin_support_bot.services.integration_service import IntegrationService
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.schemas import SupportIntent, SupportReply
from nonebot_plugin_support_bot.services.ticket_service import TicketService
from nonebot_plugin_support_bot.utils.formatter import (
    format_diagnosis_reply,
    format_followup,
    format_ticket_created,
    trim_reply,
)


class SupportBotService:
    def __init__(
        self,
        config: Config | None = None,
        intent_service: IntentService | None = None,
        integration_service: IntegrationService | None = None,
        ticket_service: TicketService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.intent_service = intent_service or IntentService(self.config)
        self.integration_service = integration_service or IntegrationService()
        self.ticket_service = ticket_service or TicketService(self.config)

    async def status(self, group_id: int | None = None) -> str:
        enabled = self.config.support_bot_enabled
        mode = self.config.support_bot_trigger_mode
        smart_listen = self.config.support_bot_enable_smart_listen
        if group_id is not None:
            async with get_session() as session:
                item = await SupportGroupConfigRepo(session, self.config).get_or_create(group_id)
                enabled = item.enabled
                mode = item.trigger_mode
                smart_listen = item.smart_listen
        return (
            "SupportBot 状态\n"
            f"插件启用：{'是' if enabled else '否'}\n"
            f"触发模式：{mode}\n"
            f"智能监听：{'开' if smart_listen else '关'}\n"
            f"软件范围：{self.config.support_bot_software_name}"
        )

    async def set_enabled(self, group_id: int, enabled: bool, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_enabled(group_id, enabled, operator_id)
            await session.commit()
        return f"SupportBot 已{'开启' if enabled else '关闭'}。"

    async def set_mode(self, group_id: int, mode: str, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_mode(group_id, mode, operator_id)
            await session.commit()
        return f"SupportBot 模式已设置为：{mode}。"

    async def is_group_enabled(self, group_id: int | None) -> bool:
        if group_id is None:
            return self.config.support_bot_enabled
        async with get_session() as session:
            item = await SupportGroupConfigRepo(session, self.config).get_or_create(group_id)
            await session.commit()
            return item.enabled

    async def should_smart_listen(self, group_id: int | None) -> bool:
        if group_id is None:
            return False
        async with get_session() as session:
            item = await SupportGroupConfigRepo(session, self.config).get_or_create(group_id)
            await session.commit()
            return item.enabled and item.smart_listen

    async def handle_user_issue(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int,
        force_log: bool = False,
        force_ticket: bool = False,
    ) -> SupportReply:
        if not await self.is_group_enabled(group_id):
            return SupportReply(text="SupportBot 当前未开启。", state="closed")

        intent = await self.intent_service.classify(text, force_log=force_log, force_ticket=force_ticket)
        if intent.reply_strategy == "ask_followup":
            await self._save_session(group_id, user_id, "collecting_environment", intent, text)
            return SupportReply(text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length), state="collecting_environment")

        if intent.should_diagnose_log:
            return await self._diagnose(text, group_id=group_id, user_id=user_id, intent=intent)

        if intent.should_create_ticket:
            ticket = await self.ticket_service.create_ticket(
                description=text,
                group_id=group_id,
                user_id=user_id,
                intent=intent,
            )
            await self._save_session(group_id, user_id, "human_handoff", intent, text)
            return SupportReply(
                text=trim_reply(format_ticket_created(ticket), self.config.support_bot_max_reply_length),
                state="human_handoff",
                ticket_no=ticket.ticket_no,
            )

        if intent.should_search_wiki:
            return await self._ask_wiki(text, group_id=group_id, user_id=user_id, intent=intent)

        await self._save_session(group_id, user_id, "collecting_issue", intent, text)
        return SupportReply(text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length), state="collecting_issue")

    async def _ask_wiki(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int,
        intent: SupportIntent,
    ) -> SupportReply:
        try:
            wiki_response = await self.integration_service.ask_wiki(text, group_id=group_id, user_id=user_id)
        except Exception as exc:
            await self._save_session(group_id, user_id, "collecting_issue", intent, text)
            return SupportReply(
                text=f"我先接住这个问题，但知识库暂时不可用：{exc}\n可以补充软件版本、系统版本、截图或日志；紧急问题可发 /人工。",
                state="collecting_issue",
            )
        references = list(getattr(wiki_response, "references", []) or [])
        answer = str(getattr(wiki_response, "answer", "")).strip()
        if references:
            text_out = f"{answer}\n\n如果还没解决，回复 /人工 或 /工单 创建 <问题>。"
            await self._save_session(group_id, user_id, "waiting_user_feedback", intent, text)
            return SupportReply(
                text=trim_reply(text_out, self.config.support_bot_max_reply_length),
                state="waiting_user_feedback",
                references=references,
                ai_used=bool(getattr(wiki_response, "ai_used", False)),
            )
        if self.config.support_bot_auto_create_ticket:
            ticket = await self.ticket_service.create_ticket(
                description=text,
                group_id=group_id,
                user_id=user_id,
                intent=intent,
            )
            return SupportReply(text=format_ticket_created(ticket), state="creating_ticket", ticket_no=ticket.ticket_no)
        await self._save_session(group_id, user_id, "collecting_environment", intent, text)
        return SupportReply(text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length), state="collecting_environment")

    async def _diagnose(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int,
        intent: SupportIntent,
    ) -> SupportReply:
        try:
            diagnosis = await self.integration_service.diagnose_log(text, group_id=group_id, user_id=user_id)
        except Exception as exc:
            await self._save_session(group_id, user_id, "collecting_log", intent, text)
            return SupportReply(
                text=f"日志我收到了，但诊断服务暂时不可用：{exc}\n你可以补充完整 Traceback，或发 /人工 转给管理员。",
                state="collecting_log",
            )
        diagnosis_no = str(getattr(diagnosis, "record_no", ""))
        result = getattr(diagnosis, "result", None)
        references: list[str] = []
        wiki_answer = ""
        try:
            title = getattr(result, "title", "")
            wiki_response = await self.integration_service.ask_wiki(title or text[:200], group_id=group_id, user_id=user_id)
            references = list(getattr(wiki_response, "references", []) or [])
            wiki_answer = str(getattr(wiki_response, "answer", "")).strip()
        except Exception:
            references = []
        await self._save_session(group_id, user_id, "waiting_user_feedback", intent, text)
        reply_text = format_diagnosis_reply(diagnosis, wiki_answer=wiki_answer, references=references)
        return SupportReply(
            text=trim_reply(reply_text, self.config.support_bot_max_reply_length),
            state="waiting_user_feedback",
            diagnosis_no=diagnosis_no,
            references=references,
            ai_used=bool(getattr(diagnosis, "ai_used", False)),
        )

    async def _save_session(
        self,
        group_id: int | None,
        user_id: int,
        state: str,
        intent: SupportIntent,
        text: str,
    ) -> None:
        async with get_session() as session:
            await SupportSessionRepo(session).upsert(
                group_id=int(group_id or 0),
                user_id=user_id,
                state=state,
                intent=intent.intent,
                context_json=json.dumps(
                    {
                        "issue_type": intent.issue_type,
                        "text": text[:1000],
                        "missing_fields": intent.missing_fields,
                    },
                    ensure_ascii=False,
                ),
                ttl_seconds=self.config.support_bot_session_ttl_seconds,
            )
            await session.commit()
