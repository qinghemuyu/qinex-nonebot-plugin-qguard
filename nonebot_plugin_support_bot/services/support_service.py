import json

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import get_session
from nonebot_plugin_support_bot.repositories.group_config_repo import SupportGroupConfigRepo
from nonebot_plugin_support_bot.repositories.session_repo import SupportSessionRepo
from nonebot_plugin_support_bot.services.integration_service import IntegrationService
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.schemas import SupportIntent, SupportReply
from nonebot_plugin_support_bot.utils.formatter import format_followup, trim_reply


class SupportBotService:
    def __init__(
        self,
        config: Config | None = None,
        intent_service: IntentService | None = None,
        integration_service: IntegrationService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.intent_service = intent_service or IntentService(self.config)
        self.integration_service = integration_service or IntegrationService()

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
            "SupportBot 知识问答状态\n"
            f"插件启用：{'是' if enabled else '否'}\n"
            f"触发模式：{mode}\n"
            f"智能监听：{'开' if smart_listen else '关'}\n"
            f"软件范围：{self.config.support_bot_software_name}\n"
            "知识范围：由 /知识 范围 控制"
        )

    async def set_enabled(self, group_id: int, enabled: bool, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_enabled(group_id, enabled, operator_id)
            await session.commit()
        return f"SupportBot 知识问答已{'开启' if enabled else '关闭'}。"

    async def set_mode(self, group_id: int, mode: str, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_mode(group_id, mode, operator_id)
            await session.commit()
        return f"SupportBot 知识问答模式已设置为：{mode}。"

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
    ) -> SupportReply:
        if not await self.is_group_enabled(group_id):
            return SupportReply(text="SupportBot 知识问答当前未开启。", state="closed")

        intent = await self.intent_service.classify(text)
        if intent.reply_strategy == "ask_followup":
            await self._save_session(group_id, user_id, "collecting_issue", intent, text)
            return SupportReply(
                text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length),
                state="collecting_issue",
            )
        return await self._ask_wiki(text, group_id=group_id, user_id=user_id, intent=intent)

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
                text=f"知识问答暂时不可用：{exc}\n可以稍后重试，或让管理员检查 /知识 导入本地 和 /知识 范围。",
                state="collecting_issue",
            )
        references = list(getattr(wiki_response, "references", []) or [])
        answer = str(getattr(wiki_response, "answer", "")).strip()
        if references:
            await self._save_session(group_id, user_id, "answered", intent, text)
            return SupportReply(
                text=trim_reply(answer, self.config.support_bot_max_reply_length),
                state="answered",
                references=references,
                ai_used=bool(getattr(wiki_response, "ai_used", False)),
            )
        await self._save_session(group_id, user_id, "no_answer", intent, text)
        return SupportReply(
            text=trim_reply(
                "当前群生效的知识库范围里没有找到可靠答案。你可以换个关键词，或让管理员用 /知识 范围 查看本群启用的知识分类。",
                self.config.support_bot_max_reply_length,
            ),
            state="no_answer",
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
                        "references": [],
                    },
                    ensure_ascii=False,
                ),
                ttl_seconds=self.config.support_bot_session_ttl_seconds,
            )
            await session.commit()
