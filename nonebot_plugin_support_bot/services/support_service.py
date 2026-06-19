import json
from hashlib import sha1
from datetime import datetime

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.models import get_session
from nonebot_plugin_support_bot.repositories.group_config_repo import SupportGroupConfigRepo
from nonebot_plugin_support_bot.repositories.issue_cluster_repo import SupportIssueClusterRepo
from nonebot_plugin_support_bot.repositories.no_answer_repo import SupportNoAnswerRepo
from nonebot_plugin_support_bot.repositories.session_repo import SupportSessionRepo
from nonebot_plugin_support_bot.services.harassment_service import HarassmentService
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
SOLVED_MARKERS = ("好了", "好啦", "解决了", "可以了", "恢复了", "能用了", "搞定了", "ok了", "OK了", "没问题了")


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
            "连续对话：按提问人隔离\n"
            f"骚扰惩罚：{'开' if self.config.support_bot_harassment_enabled else '关'}"
            f"（警告 {self.config.support_bot_harassment_warn_threshold}，积分 {self.config.support_bot_harassment_score_threshold}）\n"
            f"未解决升级：{self.config.support_bot_unresolved_escalation_turns} 轮\n"
            "反馈学习：开启\n"
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
        if previous_context is not None and _looks_like_solved_feedback(raw_text):
            return await self._finalize_reply(
                await self._handle_resolved_feedback(
                    previous_context,
                    raw_text,
                    group_id=group_id,
                    user_id=user_id,
                ),
                raw_text,
                group_id,
                user_id,
            )
        if previous_context is not None and _looks_like_continuation(raw_text, previous_context):
            question_text = _build_contextual_question(previous_context, raw_text)

        intent = await self.intent_service.classify(question_text)
        if intent.reply_strategy == "reject":
            return await self._finalize_reply(
                SupportReply(text="喵，我只回答 QInEX 映射软件相关问题。这个问题不在当前知识库范围内。", state="out_of_scope"),
                raw_text,
                group_id,
                user_id,
            )
        if intent.reply_strategy == "safe_no_answer":
            record_no = await self._record_no_answer(group_id, user_id, question_text, reason="privacy_or_license")
            return await self._finalize_reply(
                SupportReply(
                    text="喵，当前知识库没有授权/账号处理流程，我不乱猜。也不要在群里发完整授权码、订单号、密钥或隐私截图。",
                    state="no_answer",
                    no_answer_id=record_no,
                ),
                raw_text,
                group_id,
                user_id,
            )
        if intent.reply_strategy == "ask_followup":
            context = await self._save_session(
                group_id,
                user_id,
                "collecting_issue",
                intent,
                question_text,
                user_text=raw_text,
                previous_context=previous_context,
            )
            reply = self._attach_owner_escalation(
                SupportReply(
                    text=trim_reply(format_followup(intent), self.config.support_bot_max_reply_length),
                    state="collecting_issue",
                ),
                context,
                group_id=group_id,
                user_id=user_id,
            )
            return await self._finalize_reply(
                reply,
                raw_text,
                group_id,
                user_id,
            )
        reply = await self._ask_wiki(
            question_text,
            group_id=group_id,
            user_id=user_id,
            intent=intent,
            user_text=raw_text,
            previous_context=previous_context,
        )
        return await self._finalize_reply(reply, raw_text, group_id, user_id)

    async def should_handle_continuation(self, text: str, *, group_id: int | None, user_id: int) -> bool:
        stripped = text.strip()
        if group_id is None or not stripped or stripped.startswith("/"):
            return False
        if not _could_be_continuation_candidate(stripped):
            return False
        if not await self._is_group_enabled_without_create(group_id):
            return False
        previous_context = await self._recent_context(group_id, user_id)
        return previous_context is not None and _looks_like_continuation(stripped, previous_context)

    async def _is_group_enabled_without_create(self, group_id: int | None) -> bool:
        if group_id is None:
            return self.config.support_bot_enabled
        async with get_session() as session:
            item = await SupportGroupConfigRepo(session, self.config).get(group_id)
            return self.config.support_bot_enabled if item is None else item.enabled

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
            search_query = _build_search_query(text=text, user_text=user_text, previous_context=previous_context)
            wiki_response = await self.integration_service.ask_wiki(
                text,
                group_id=group_id,
                user_id=user_id,
                search_query=search_query,
            )
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
            context = await self._save_session(
                group_id,
                user_id,
                "answered",
                intent,
                text,
                user_text=user_text,
                previous_context=previous_context,
                references=references,
            )
            await self._record_issue_cluster(context, group_id=group_id, user_id=user_id)
            return self._attach_owner_escalation(
                SupportReply(
                    text=trim_reply(answer, self.config.support_bot_max_reply_length),
                    state="answered",
                    references=references,
                    ai_used=bool(getattr(wiki_response, "ai_used", False)),
                ),
                context,
                group_id=group_id,
                user_id=user_id,
            )
        context = await self._save_session(
            group_id,
            user_id,
            "no_answer",
            intent,
            text,
            user_text=user_text,
            previous_context=previous_context,
        )
        record_no = await self._record_no_answer(group_id, user_id, text, reason="no_knowledge")
        await self._record_issue_cluster(
            context,
            group_id=group_id,
            user_id=user_id,
            no_answer=True,
            record_no=record_no,
        )
        return self._attach_owner_escalation(
            SupportReply(
                text=trim_reply(
                    "喵，当前群生效的知识库范围里没有找到可靠答案。我已经把这个问题记下来给主人看啦。你也可以换个关键词，或让管理员用 /知识 范围 查看本群启用的知识分类。",
                    self.config.support_bot_max_reply_length,
                ),
                state="no_answer",
                no_answer_id=record_no,
            ),
            context,
            group_id=group_id,
            user_id=user_id,
        )

    def _attach_owner_escalation(
        self,
        reply: SupportReply,
        context: dict,
        *,
        group_id: int | None,
        user_id: int,
    ) -> SupportReply:
        threshold = self.config.support_bot_unresolved_escalation_turns
        if threshold <= 0:
            return reply
        if bool(context.get("owner_escalation_notified")):
            return reply
        turn_count = int(context.get("issue_turn_count") or 1)
        if turn_count < threshold:
            return reply
        reply.owner_escalation = True
        reply.owner_escalation_turns = turn_count
        reply.owner_escalation_summary = _build_owner_escalation_summary(
            context,
            group_id=group_id,
            user_id=user_id,
            latest_reply=reply.text,
        )
        return reply

    async def _handle_resolved_feedback(
        self,
        previous_context: dict,
        raw_text: str,
        *,
        group_id: int | None,
        user_id: int,
    ) -> SupportReply:
        context = dict(previous_context)
        context["owner_escalation_notified"] = bool(context.get("owner_escalation_notified"))
        await self._record_issue_cluster(
            context,
            group_id=group_id,
            user_id=user_id,
            resolved=True,
        )
        await self._save_resolution_session(group_id, user_id, context, raw_text)
        return SupportReply(
            text="喵，收到，已把这次处理记为“已解决”。以后类似问题我会更偏向这条排查路线。",
            state="resolved_feedback",
        )

    async def _record_issue_cluster(
        self,
        context: dict,
        *,
        group_id: int | None,
        user_id: int,
        no_answer: bool = False,
        unresolved: bool = False,
        resolved: bool = False,
        record_no: str = "",
    ) -> None:
        cluster_key = str(context.get("cluster_key") or "").strip()
        if not cluster_key:
            return
        async with get_session() as session:
            await SupportIssueClusterRepo(session).record(
                cluster_key=cluster_key,
                title=str(context.get("cluster_title") or context.get("issue_started_text") or "未知问题"),
                skill=str(context.get("skill") or "unknown"),
                issue_type=str(context.get("issue_type") or "unknown"),
                question=str(context.get("issue_started_text") or context.get("text") or ""),
                group_id=int(group_id or 0),
                user_id=user_id,
                no_answer=no_answer,
                unresolved=unresolved,
                resolved=resolved,
                record_no=record_no,
            )
            await session.commit()

    async def _finalize_reply(
        self,
        reply: SupportReply,
        raw_text: str,
        group_id: int | None,
        user_id: int,
    ) -> SupportReply:
        evaluation = await HarassmentService(self.config).record_if_needed(
            raw_text,
            group_id=group_id,
            user_id=user_id,
            reply_state=reply.state,
        )
        if not evaluation.hit:
            return reply
        reply.harassment_anger = evaluation.anger_score
        reply.harassment_score_delta = evaluation.score_delta
        reply.harassment_reason = evaluation.reason
        notice = _format_harassment_notice(
            evaluation.score_delta,
            evaluation.anger_score,
            evaluation.severity,
            self.config.support_bot_harassment_warn_threshold,
        )
        if notice:
            reply.text = trim_reply(f"{reply.text}\n{notice}", self.config.support_bot_max_reply_length)
        return reply

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
    ) -> dict:
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
        return context

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

    async def mark_issue_escalation_notified(self, group_id: int | None, user_id: int) -> None:
        if group_id is None:
            return
        now = datetime.utcnow()
        context: dict | None = None
        async with get_session() as session:
            item = await SupportSessionRepo(session).get_active(int(group_id), user_id, now)
            if item is None:
                return
            try:
                context = json.loads(item.context_json or "{}")
            except json.JSONDecodeError:
                context = {}
            if not isinstance(context, dict):
                context = {}
            context["owner_escalation_notified"] = True
            item.context_json = json.dumps(context, ensure_ascii=False)
            await session.commit()
        await self._record_issue_cluster(context, group_id=group_id, user_id=user_id, unresolved=True)

    async def _save_resolution_session(
        self,
        group_id: int | None,
        user_id: int,
        previous_context: dict,
        raw_text: str,
    ) -> None:
        context = dict(previous_context)
        turns = context.get("turns")
        if not isinstance(turns, list):
            turns = []
        turns = [turn for turn in turns if isinstance(turn, dict)][-9:]
        turns.append({"state": "resolved_feedback", "user": raw_text[:500], "question": raw_text[:500], "references": []})
        context["turns"] = turns[-10:]
        context["latest_user_text"] = raw_text[:500]
        context["resolved"] = True
        context["owner_escalation_notified"] = bool(context.get("owner_escalation_notified"))
        async with get_session() as session:
            await SupportSessionRepo(session).upsert(
                group_id=int(group_id or 0),
                user_id=user_id,
                state="resolved_feedback",
                intent=str(context.get("_intent") or "resolved_feedback"),
                context_json=json.dumps(context, ensure_ascii=False),
                ttl_seconds=self.config.support_bot_session_ttl_seconds,
            )
            await session.commit()

    async def issue_gaps(self, limit: int = 5) -> str:
        async with get_session() as session:
            clusters = await SupportIssueClusterRepo(session).list_hot(limit=limit)
        if not clusters:
            return "暂无智能问答缺口记录。"
        top = clusters[0]
        lines = [
            "QInEX 智能问答缺口看板",
            f"优先处理：{top.title or top.example_question[:30]}",
            f"原因：未解决 {top.unresolved_count} 次，未命中 {top.no_answer_count} 次，出现 {top.occurrence_count} 次。",
            "",
            "TOP 问题：",
        ]
        for index, item in enumerate(clusters, start=1):
            priority = _issue_priority(item)
            lines.append(
                f"{index}. {item.title or item.example_question[:30]}（优先级 {priority}）\n"
                f"   分类：{item.skill}/{item.issue_type}，出现 {item.occurrence_count}，未命中 {item.no_answer_count}，未解决 {item.unresolved_count}，已解决 {item.resolved_count}\n"
                f"   最近问题：{item.last_question[:80]}"
            )
            if item.last_record_no:
                lines.append(f"   下一步：/客服 补知识 {item.last_record_no} 答案内容")
            elif item.unresolved_count:
                lines.append("   下一步：复盘连续未解决对话，补一条问诊流程或知识库答案。")
            else:
                lines.append("   下一步：观察用户是否继续追问；如果反复出现再补知识。")
        return "\n".join(lines)

    async def supplement_no_answer(
        self,
        record_no: str,
        answer: str,
        *,
        author_id: int | None,
        group_id: int | None = None,
    ) -> str:
        normalized_record_no = record_no.strip().upper()
        answer = answer.strip()
        if not normalized_record_no or not answer:
            return "用法：/客服 补知识 N000001 答案内容"
        async with get_session() as session:
            item = await SupportNoAnswerRepo(session).get_by_record_no(normalized_record_no)
            if item is None:
                return "没有找到这条未命中记录。"
            question = item.question
            item.notified_owner = True
            item.updated_at = datetime.utcnow()
            await session.commit()
        try:
            from nonebot_plugin_group_wiki.services.article_service import GroupWikiService
        except ModuleNotFoundError as exc:
            if exc.name and not exc.name.startswith("nonebot_plugin_group_wiki"):
                raise
            return "知识库插件未加载，暂时不能补知识。"

        title = _title_from_question(question)
        content = (
            f"## 用户常见问法\n{question.strip()[:1200]}\n\n"
            f"## 推荐回答\n{answer[:3000]}\n\n"
            "## 回复边界\n"
            "只按这里的公开使用步骤回答，不展开授权码、密钥、算法或内部实现细节。"
        )
        article = await GroupWikiService().add_article(
            title=title,
            content=content,
            group_id=group_id,
            author_id=author_id,
            scope="global",
            source_type="support_no_answer",
            source_ref_id=normalized_record_no,
            category="FAQ问答对",
            summary=answer[:180],
        )
        return f"已补充知识：[{article.article_no}] {article.title}\n建议执行 /知识 搜索 {title[:20]} 验证命中。"


def _looks_like_continuation(text: str, previous_context: dict | None = None) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _looks_like_solved_feedback(stripped):
        return True
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
        "没有",
        "电脑",
        "手机",
        "投屏",
        "滑屏",
        "压枪",
        "连点",
    )
    return len(stripped) <= 30 and any(marker in normalized for marker in short_fact_markers)


def _issue_priority(item) -> int:
    return max(
        0,
        int(getattr(item, "unresolved_count", 0) or 0) * 5
        + int(getattr(item, "no_answer_count", 0) or 0) * 3
        + int(getattr(item, "occurrence_count", 0) or 0)
        - int(getattr(item, "resolved_count", 0) or 0) * 2,
    )


def _could_be_continuation_candidate(text: str) -> bool:
    stripped = text.strip()
    if not stripped or any(marker in stripped for marker in RESET_MARKERS):
        return False
    if _looks_like_solved_feedback(stripped):
        return True
    normalized = stripped.lower()
    if stripped in THANKS_MARKERS or normalized in {marker.lower() for marker in THANKS_MARKERS}:
        return False
    if any(marker in stripped for marker in CONTINUATION_MARKERS):
        return True
    quick_markers = (
        "s3",
        "p4",
        "adb",
        "免硬件",
        "硬件",
        "数据线",
        "管理员",
        "开了",
        "没开",
        "没有",
        "电脑",
        "手机",
        "投屏",
        "滑屏",
        "压枪",
        "连点",
        "截图",
        "版本",
    )
    return len(stripped) <= 30 and any(marker in normalized for marker in quick_markers)


def _looks_like_solved_feedback(text: str) -> bool:
    stripped = text.strip()
    normalized = stripped.lower()
    return any(marker in stripped for marker in SOLVED_MARKERS) or any(
        marker.lower() in normalized for marker in SOLVED_MARKERS
    )


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


def _build_search_query(*, text: str, user_text: str | None, previous_context: dict | None) -> str:
    if previous_context is None:
        return text
    previous_question = str(previous_context.get("text") or previous_context.get("latest_user_text") or "").strip()
    current = str(user_text or "").strip()
    if previous_question and current:
        return f"{previous_question}\n{current}"
    return current or previous_question or text


def _build_session_context(
    *,
    intent: SupportIntent,
    text: str,
    user_text: str,
    previous_context: dict | None,
    state: str,
    references: list[str],
) -> dict:
    same_issue = _is_same_issue(intent, user_text, previous_context)
    turns = []
    issue_turn_count = 1
    issue_started_text = text[:1000]
    owner_escalation_notified = False
    if previous_context is not None:
        if same_issue:
            raw_turns = previous_context.get("turns")
            if isinstance(raw_turns, list):
                turns = [turn for turn in raw_turns if isinstance(turn, dict)][-9:]
            issue_turn_count = int(previous_context.get("issue_turn_count") or len(turns) or 1) + 1
            issue_started_text = str(previous_context.get("issue_started_text") or previous_context.get("text") or text)[
                :1000
            ]
            owner_escalation_notified = bool(previous_context.get("owner_escalation_notified"))
    cluster_key, cluster_title = _build_issue_cluster(intent, issue_started_text)
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
        "turns": turns[-10:],
        "issue_turn_count": issue_turn_count,
        "issue_started_text": issue_started_text,
        "cluster_key": cluster_key,
        "cluster_title": cluster_title,
        "owner_escalation_notified": owner_escalation_notified,
    }


ISSUE_CLUSTER_ANCHORS = (
    "校准",
    "触摸校准",
    "坐标",
    "黑边",
    "分辨率",
    "部分按键",
    "按键",
    "鼠标",
    "摇杆",
    "wasd",
    "滑屏",
    "卡顿",
    "掉帧",
    "投屏",
    "screenhub",
    "qinescreen",
    "p4",
    "s3",
    "adb",
    "免硬件",
    "压枪",
    "连点",
    "开镜",
    "激活",
    "打不开",
    "闪退",
    "webview2",
    "没反应",
    "不生效",
    "失效",
    "点不准",
)


def _build_issue_cluster(intent: SupportIntent, text: str) -> tuple[str, str]:
    normalized = text.lower()
    anchors = [anchor for anchor in ISSUE_CLUSTER_ANCHORS if anchor.lower() in normalized]
    if not anchors:
        compact = "".join(ch.lower() for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
        digest = sha1(compact[:120].encode("utf-8")).hexdigest()[:10] if compact else "unknown"
        anchors = [digest]
    anchors = anchors[:4]
    issue_type = intent.issue_type or "unknown"
    skill = intent.skill or "unknown"
    cluster_key = f"{skill}:{issue_type}:{'|'.join(anchors)}"
    title = " / ".join(anchors)
    if title.startswith("unknown") or len(title) < 4:
        title = _title_from_question(text)
    return cluster_key[:128], title[:80]


def _title_from_question(text: str) -> str:
    compact = " ".join(text.strip().split())
    if not compact:
        return "未命中问题补充"
    return compact[:40]


def _is_same_issue(intent: SupportIntent, user_text: str, previous_context: dict | None) -> bool:
    if previous_context is None:
        return False
    if any(marker in user_text for marker in RESET_MARKERS):
        return False
    if _looks_like_continuation(user_text, previous_context):
        return True
    previous_skill = str(previous_context.get("skill") or "")
    previous_issue_type = str(previous_context.get("issue_type") or "")
    if not previous_skill or not previous_issue_type or previous_issue_type == "unknown":
        return False
    if previous_skill != intent.skill or previous_issue_type != intent.issue_type:
        return False
    previous_text = str(previous_context.get("issue_started_text") or previous_context.get("text") or "")
    return _has_meaningful_overlap(previous_text, user_text)


def _has_meaningful_overlap(previous_text: str, current_text: str) -> bool:
    previous_terms = _text_bigrams(previous_text)
    current_terms = _text_bigrams(current_text)
    if not previous_terms or not current_terms:
        return False
    overlap = previous_terms.intersection(current_terms)
    return len(overlap) >= 2 or len(overlap) / max(len(current_terms), 1) >= 0.35


def _text_bigrams(text: str) -> set[str]:
    normalized = "".join(ch.lower() for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def _build_owner_escalation_summary(
    context: dict,
    *,
    group_id: int | None,
    user_id: int,
    latest_reply: str,
) -> str:
    turns = [turn for turn in context.get("turns", []) if isinstance(turn, dict)]
    recent_user_texts = _unique_nonempty(str(turn.get("user") or "") for turn in turns[-6:])
    references = _unique_nonempty(
        str(reference)
        for turn in turns
        for reference in (turn.get("references") if isinstance(turn.get("references"), list) else [])
    )
    lines = [
        "QInEX 智能问答连续未解决",
        f"群：{group_id or '私聊'}",
        f"用户：{user_id}",
        f"轮数：{int(context.get('issue_turn_count') or len(turns) or 1)}",
        f"分类：{context.get('skill') or 'unknown'} / {context.get('issue_type') or 'unknown'}",
        f"最初问题：{str(context.get('issue_started_text') or context.get('text') or '').strip()[:500]}",
    ]
    if recent_user_texts:
        lines.append("最近补充：")
        lines.extend(f"{index}. {text[:180]}" for index, text in enumerate(recent_user_texts, start=1))
    if references:
        lines.append(f"命中过的知识：{'，'.join(references[:5])}")
    lines.append(f"机器人最新回复：{latest_reply.strip()[:500]}")
    lines.append("建议：主人介入看一下，必要时补知识库或让用户发截图/版本/模式信息。")
    return "\n".join(lines)


def _unique_nonempty(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _format_harassment_notice(score_delta: int, anger_score: int, severity: int, warn_threshold: int) -> str:
    if score_delta > 0:
        return "喵，忍耐值掉光了，这次我先记下，交给群管积分处理。"
    if severity >= 3:
        return "喵，骂客服我会记仇的，再来就要进群管积分了。"
    if anger_score >= warn_threshold:
        return "喵，别一直拿我开涮，我已经开始记仇了。"
    return ""
