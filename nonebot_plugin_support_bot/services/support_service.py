import json
from datetime import datetime

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import get_session
from nonebot_plugin_support_bot.repositories.group_config_repo import SupportGroupConfigRepo
from nonebot_plugin_support_bot.repositories.no_answer_repo import SupportNoAnswerRepo
from nonebot_plugin_support_bot.repositories.session_repo import SupportSessionRepo
from nonebot_plugin_support_bot.services.integration_service import IntegrationService
from nonebot_plugin_support_bot.services.intent_service import IntentService
from nonebot_plugin_support_bot.services.schemas import SupportIntent, SupportReply
from nonebot_plugin_support_bot.utils.formatter import format_followup, trim_reply

CONTINUATION_MARKERS = (
    "还是不行",
    "还是不可以",
    "依旧不行",
    "仍然不行",
    "还是没用",
    "没有用",
    "没用",
    "没效果",
    "没变化",
    "试了",
    "照做",
    "按你说的",
    "按这个",
    "然后呢",
    "下一步",
    "继续",
    "还是卡",
    "依旧卡",
    "仍然卡",
    "还卡",
    "不生效",
    "没反应",
)
RESET_MARKERS = ("新问题", "另一个问题", "换个问题", "不是这个", "重新问")
THANKS_MARKERS = ("谢谢", "感谢", "ok", "OK", "好的", "好嘞", "明白", "懂了", "可以了", "解决了")


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
            "QInEX 智能问答状态\n"
            f"插件启用：{'是' if enabled else '否'}\n"
            f"触发模式：{mode}\n"
            f"智能监听：{'开' if smart_listen else '关'}\n"
            f"连续对话：{self.config.support_bot_conversation_ttl_seconds} 秒\n"
            f"软件范围：{self.config.support_bot_software_name}\n"
            "知识范围：由 /知识 范围 控制\n"
            "技能列表：用 /知识 技能 查看"
        )

    async def set_enabled(self, group_id: int, enabled: bool, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_enabled(group_id, enabled, operator_id)
            await session.commit()
        return f"QInEX 智能问答已{'开启' if enabled else '关闭'}。"

    async def set_mode(self, group_id: int, mode: str, operator_id: int | None) -> str:
        async with get_session() as session:
            await SupportGroupConfigRepo(session, self.config).set_mode(group_id, mode, operator_id)
            await session.commit()
        return f"QInEX 智能问答模式已设置为：{mode}。"

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
            return SupportReply(text="喵，QInEX 智能问答当前还没开启。", state="closed")

        raw_text = text.strip()
        previous_context = await self._recent_context(group_id, user_id)
        question_text = raw_text
        if previous_context is not None and _looks_like_continuation(raw_text, previous_context):
            question_text = _build_contextual_question(previous_context, raw_text)

        intent = await self.intent_service.classify(question_text)
        if intent.reply_strategy == "reject":
            return SupportReply(text="喵，我只回答 QInEX 映射软件相关问题。这个问题不在当前知识库范围内。", state="out_of_scope")
        if intent.reply_strategy == "safe_no_answer":
            record_no = await self._record_no_answer(group_id, user_id, question_text, reason="privacy_or_license")
            return SupportReply(
                text="喵，当前知识库没有授权/账号处理流程，我不乱猜。也不要在群里发完整授权码、订单号、密钥或隐私截图。",
                state="no_answer",
                no_answer_id=record_no,
            )
        if intent.reply_strategy == "ask_followup":
            await self._save_session(
                group_id,
                user_id,
                "collecting_issue",
                intent,
                question_text,
                user_text=raw_text,
                previous_context=previous_context,
            )
            return SupportReply(
                text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length),
                state="collecting_issue",
            )
        return await self._ask_wiki(
            question_text,
            group_id=group_id,
            user_id=user_id,
            intent=intent,
            user_text=raw_text,
            previous_context=previous_context,
        )

    async def should_handle_continuation(self, text: str, *, group_id: int | None, user_id: int) -> bool:
        stripped = text.strip()
        if group_id is None or not stripped or stripped.startswith("/"):
            return False
        if not await self.is_group_enabled(group_id):
            return False
        previous_context = await self._recent_context(group_id, user_id)
        return previous_context is not None and _looks_like_continuation(stripped, previous_context)

    async def _ask_wiki(
        self,
        text: str,
        *,
        group_id: int | None,
        user_id: int,
        intent: SupportIntent,
        user_text: str | None = None,
        previous_context: dict | None = None,
    ) -> SupportReply:
        try:
            wiki_response = await self.integration_service.ask_wiki(text, group_id=group_id, user_id=user_id)
        except Exception as exc:
            await self._save_session(
                group_id,
                user_id,
                "collecting_issue",
                intent,
                text,
                user_text=user_text,
                previous_context=previous_context,
            )
            return SupportReply(
                text=f"喵，知识问答暂时不可用：{exc}\n可以稍后重试，或让管理员检查 /知识 导入本地 和 /知识 范围。",
                state="collecting_issue",
            )
        references = list(getattr(wiki_response, "references", []) or [])
        answer = str(getattr(wiki_response, "answer", "")).strip()
        if references:
            await self._save_session(
                group_id,
                user_id,
                "answered",
                intent,
                text,
                user_text=user_text,
                previous_context=previous_context,
                references=references,
            )
            return SupportReply(
                text=trim_reply(answer, self.config.support_bot_max_reply_length),
                state="answered",
                references=references,
                ai_used=bool(getattr(wiki_response, "ai_used", False)),
            )
        await self._save_session(
            group_id,
            user_id,
            "no_answer",
            intent,
            text,
            user_text=user_text,
            previous_context=previous_context,
        )
        record_no = await self._record_no_answer(group_id, user_id, text, reason="no_knowledge")
        return SupportReply(
            text=trim_reply(
                "喵，当前群生效的知识库范围里没有找到可靠答案。我已经把这个问题记下来给主人看啦。你也可以换个关键词，或让管理员用 /知识 范围 查看本群启用的知识分类。",
                self.config.support_bot_max_reply_length,
            ),
            state="no_answer",
            no_answer_id=record_no,
        )

    async def _save_session(
        self,
        group_id: int | None,
        user_id: int,
        state: str,
        intent: SupportIntent,
        text: str,
        user_text: str | None = None,
        previous_context: dict | None = None,
        references: list[str] | None = None,
    ) -> None:
        context = _build_session_context(
            intent=intent,
            text=text,
            user_text=user_text or text,
            previous_context=previous_context,
            state=state,
            references=references or [],
        )
        async with get_session() as session:
            await SupportSessionRepo(session).upsert(
                group_id=int(group_id or 0),
                user_id=user_id,
                state=state,
                intent=intent.intent,
                context_json=json.dumps(context, ensure_ascii=False),
                ttl_seconds=self.config.support_bot_session_ttl_seconds,
            )
            await session.commit()

    async def _recent_context(self, group_id: int | None, user_id: int) -> dict | None:
        if group_id is None or self.config.support_bot_conversation_ttl_seconds <= 0:
            return None
        now = datetime.utcnow()
        async with get_session() as session:
            item = await SupportSessionRepo(session).get_active(int(group_id), user_id, now)
            if item is None:
                return None
            seconds_since_active = (now - item.last_active_at).total_seconds()
            if seconds_since_active > self.config.support_bot_conversation_ttl_seconds:
                return None
            try:
                context = json.loads(item.context_json or "{}")
            except json.JSONDecodeError:
                context = {}
            if not isinstance(context, dict):
                context = {}
            context["_state"] = item.state
            context["_intent"] = item.intent
            return context

    async def _record_no_answer(self, group_id: int | None, user_id: int, text: str, *, reason: str) -> str:
        async with get_session() as session:
            item = await SupportNoAnswerRepo(session).create(
                group_id=int(group_id or 0),
                user_id=user_id,
                question=text,
                reason=reason,
            )
            await session.commit()
            return item.record_no

    async def mark_no_answer_notified(self, record_no: str) -> None:
        if not record_no:
            return
        async with get_session() as session:
            await SupportNoAnswerRepo(session).mark_notified(record_no)
            await session.commit()


def _looks_like_continuation(text: str, previous_context: dict | None = None) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    normalized = stripped.lower()
    if any(marker in stripped for marker in RESET_MARKERS):
        return False
    if stripped in THANKS_MARKERS or normalized in {marker.lower() for marker in THANKS_MARKERS}:
        return False
    if any(marker in stripped for marker in CONTINUATION_MARKERS):
        return True
    previous_state = str((previous_context or {}).get("_state") or "")
    if previous_state == "collecting_issue" and len(stripped) <= 80:
        return True
    short_fact_markers = (
        "s3",
        "p4",
        "adb",
        "免硬件",
        "硬件",
        "数据线",
        "管理员",
        "开了",
        "没开",
        "有",
        "没有",
        "电脑",
        "手机",
        "投屏",
        "滑屏",
        "压枪",
        "连点",
        "卡",
    )
    return len(stripped) <= 30 and any(marker in normalized for marker in short_fact_markers)


def _build_contextual_question(previous_context: dict, user_text: str) -> str:
    previous_question = str(previous_context.get("text") or previous_context.get("latest_user_text") or "").strip()
    previous_skill = str(previous_context.get("skill") or "unknown").strip()
    previous_issue_type = str(previous_context.get("issue_type") or "unknown").strip()
    if not previous_question:
        return user_text.strip()
    return (
        "这是同一个用户在短时间内的连续追问，请结合上一轮问题回答。\n"
        f"上一轮问题：{previous_question[:1000]}\n"
        f"上一轮分类：{previous_skill} / {previous_issue_type}\n"
        f"用户补充：{user_text.strip()[:500]}\n"
        "请基于当前群可用知识库给出下一步排查。"
    )


def _build_session_context(
    *,
    intent: SupportIntent,
    text: str,
    user_text: str,
    previous_context: dict | None,
    state: str,
    references: list[str],
) -> dict:
    turns = []
    if previous_context is not None:
        raw_turns = previous_context.get("turns")
        if isinstance(raw_turns, list):
            turns = [turn for turn in raw_turns if isinstance(turn, dict)][-3:]
    turns.append(
        {
            "state": state,
            "user": user_text[:500],
            "question": text[:1000],
            "references": references[:5],
        }
    )
    return {
        "issue_type": intent.issue_type,
        "skill": intent.skill,
        "text": text[:1000],
        "latest_user_text": user_text[:500],
        "references": references[:5],
        "turns": turns[-4:],
    }
