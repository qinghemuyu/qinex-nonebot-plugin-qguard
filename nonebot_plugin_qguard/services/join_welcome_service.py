from dataclasses import dataclass

from nonebot_plugin_qguard.adapter.group_ops import GroupOps
from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.services.auto_recall_service import AUTO_RECALL_CHAT
from nonebot_plugin_qguard.services.result import ActionResult

DEFAULT_JOIN_WELCOME_TEMPLATE = """欢迎 {at_user} 入群

进群方式：{join_method}
邀请人：{inviter}
审批人：{approver}

请先看看群公告、群文件和群内教程。
遇到问题可以直接艾特机器人，把现象、设备类型、软件版本和已经试过的操作说清楚。"""


@dataclass(frozen=True)
class JoinWelcomeContext:
    group_id: int
    user_id: int
    sub_type: str
    operator_id: int | None = None
    bot_self_id: int | None = None


class JoinWelcomeService:
    async def set_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_join_welcome_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_JOIN_WELCOME,
                result=AuditResult.SUCCESS,
                metadata={"join_welcome_enabled": enabled},
            )
            await session.commit()
        return ActionResult(
            success=True,
            action=str(AuditAction.SET_JOIN_WELCOME),
            message=f"入群欢迎已{'开启' if config.join_welcome_enabled else '关闭'}。",
        )

    async def set_template(self, group_id: int, operator_id: int, template: str) -> ActionResult:
        template = template.strip()
        if template in {"默认", "default"}:
            template = ""
        if len(template) > 1000:
            return ActionResult(
                success=False,
                action=str(AuditAction.SET_JOIN_WELCOME_TEMPLATE),
                message="入群欢迎模板不能超过 1000 个字符。",
            )

        async with get_session() as session:
            await GroupConfigRepo(session).set_join_welcome_template(group_id, template)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_JOIN_WELCOME_TEMPLATE,
                result=AuditResult.SUCCESS,
                metadata={"template_length": len(template), "use_default": not template},
            )
            await session.commit()
        message = "入群欢迎模板已恢复默认。" if not template else "入群欢迎模板已设置。"
        return ActionResult(success=True, action=str(AuditAction.SET_JOIN_WELCOME_TEMPLATE), message=message)

    async def status(self, group_id: int) -> str:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            await session.commit()
        template_state = "默认模板" if not config.join_welcome_template.strip() else "自定义模板"
        return f"入群欢迎：{'开' if config.join_welcome_enabled else '关'}，模板：{template_state}。"

    async def send_welcome_if_enabled(self, ops: GroupOps, context: JoinWelcomeContext) -> bool:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(context.group_id)
            if not config.enabled or not config.join_welcome_enabled:
                await session.commit()
                return False
            template = config.join_welcome_template.strip() or DEFAULT_JOIN_WELCOME_TEMPLATE
            message = self.render_welcome(template, context)
            await session.commit()

        try:
            await ops.send_group_msg(context.group_id, message, message_category=AUTO_RECALL_CHAT)
        except Exception as exc:
            async with get_session() as session:
                await AuditLogRepo(session).create(
                    group_id=context.group_id,
                    target_user_id=context.user_id,
                    operator_id=context.operator_id,
                    action=AuditAction.JOIN_WELCOME_SEND,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"sub_type": context.sub_type},
                )
                await session.commit()
            raise

        async with get_session() as session:
            await AuditLogRepo(session).create(
                group_id=context.group_id,
                target_user_id=context.user_id,
                operator_id=context.operator_id,
                action=AuditAction.JOIN_WELCOME_SEND,
                result=AuditResult.SUCCESS,
                metadata={"sub_type": context.sub_type},
            )
            await session.commit()
        return True

    def render_welcome(self, template: str, context: JoinWelcomeContext) -> str:
        values = {
            "at_user": _at(context.user_id),
            "user_id": str(context.user_id),
            "join_method": _join_method_label(context.sub_type),
            "inviter": _inviter_label(context),
            "approver": _approver_label(context),
            "operator": _operator_label(context),
        }
        return _safe_format(template, values)


def _safe_format(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _at(user_id: int) -> str:
    return f"[CQ:at,qq={user_id}]"


def _join_method_label(sub_type: str) -> str:
    return {
        "invite": "邀请入群",
        "approve": "申请入群",
        "add": "主动申请",
    }.get(sub_type, f"未知方式（{sub_type or '未上报'}）")


def _inviter_label(context: JoinWelcomeContext) -> str:
    if context.sub_type != "invite":
        return "无"
    return _operator_label(context)


def _approver_label(context: JoinWelcomeContext) -> str:
    if context.sub_type != "approve":
        return "无"
    if context.bot_self_id and context.operator_id == context.bot_self_id:
        return "QGuard 自动审核"
    return _operator_label(context)


def _operator_label(context: JoinWelcomeContext) -> str:
    if not context.operator_id or context.operator_id == context.user_id:
        return "未上报"
    return _at(context.operator_id)
