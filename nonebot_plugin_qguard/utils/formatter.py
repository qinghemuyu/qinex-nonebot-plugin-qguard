from nonebot_plugin_qguard.models.audit_log import AuditLog
from nonebot_plugin_qguard.models.group_config import GroupConfig


def format_group_status(config: GroupConfig) -> str:
    auto_delete_text = "关闭" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds} 秒"
    join_answer_text = "已设置" if config.join_review_answer.strip() else "未设置"
    newbie_rules = ["链接"] if config.newbie_block_links else []
    if config.newbie_block_images:
        newbie_rules.append("图片")
    newbie_rule_text = "、".join(newbie_rules) if newbie_rules else "未拦截"
    return (
        "QGuard 状态\n"
        f"插件启用：{'是' if config.enabled else '否'}\n"
        f"名片锁：{'是' if config.card_lock_enabled else '否'}\n"
        f"入群审核：{'是' if config.join_review_enabled else '否'}（暗号{join_answer_text}）\n"
        f"新人保护：{'是' if config.new_member_protection_enabled else '否'}（{config.newbie_protection_seconds} 秒，拦截{newbie_rule_text}）\n"
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
