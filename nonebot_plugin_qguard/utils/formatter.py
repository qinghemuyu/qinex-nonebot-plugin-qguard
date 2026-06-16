from nonebot_plugin_qguard.models.audit_log import AuditLog
from nonebot_plugin_qguard.models.group_config import GroupConfig


def format_group_status(config: GroupConfig) -> str:
    auto_delete_text = "关闭" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds} 秒"
    return (
        "QGuard 状态\n"
        f"插件启用：{'是' if config.enabled else '否'}\n"
        f"名片锁：{'是' if config.card_lock_enabled else '否'}\n"
        f"自动审核：{'是' if config.auto_moderation_enabled else '否'}\n"
        f"默认禁言：{config.default_mute_seconds} 秒\n"
        f"自动撤回：{auto_delete_text}"
    )


def format_audit_logs(logs: list[AuditLog]) -> str:
    if not logs:
        return "暂无审计日志。"
    lines = ["最近审计日志："]
    for item in logs:
        target = f" -> {item.target_user_id}" if item.target_user_id else ""
        error = f"，错误：{item.error_message}" if item.error_message else ""
        lines.append(f"#{item.id} {item.action} {item.result} {item.operator_id}{target}{error}")
    return "\n".join(lines)
