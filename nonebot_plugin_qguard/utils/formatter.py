from nonebot_plugin_qguard.models.audit_log import AuditLog
from nonebot_plugin_qguard.models.group_config import GroupConfig
from nonebot_plugin_qguard.models.message_cache import MessageCache
from nonebot_plugin_qguard.services.auto_recall_service import (
    deserialize_auto_recall_categories,
    format_auto_recall_categories,
)


def format_group_status(config: GroupConfig) -> str:
    auto_delete_text = "关闭" if config.auto_delete_reply_seconds <= 0 else f"{config.auto_delete_reply_seconds} 秒"
    auto_delete_categories = format_auto_recall_categories(
        deserialize_auto_recall_categories(config.auto_delete_reply_categories)
    )
    join_answer_text = "已设置" if config.join_review_answer.strip() else "未设置"
    newbie_rules = ["链接"] if config.newbie_block_links else []
    if config.newbie_block_images:
        newbie_rules.append("图片")
    newbie_rule_text = "、".join(newbie_rules) if newbie_rules else "未拦截"
    group_name_lock_text = f"是（{config.locked_group_name}）" if config.group_name_lock_enabled else "否"
    anonymous_lock_text = f"是（{'开' if config.anonymous_enabled else '关'}）" if config.anonymous_lock_enabled else "否"
    auto_patrol_text = (
        f"是（{config.auto_patrol_interval_seconds} 秒）" if config.auto_patrol_enabled else "否"
    )
    return (
        "QGuard 状态\n"
        f"插件启用：{'是' if config.enabled else '否'}\n"
        f"名片锁：{'是' if config.card_lock_enabled else '否'}\n"
        f"群名锁：{group_name_lock_text}\n"
        f"匿名锁：{anonymous_lock_text}\n"
        f"自动巡检：{auto_patrol_text}\n"
        f"入群审核：{'是' if config.join_review_enabled else '否'}（暗号{join_answer_text}）\n"
        f"新人保护：{'是' if config.new_member_protection_enabled else '否'}（{config.newbie_protection_seconds} 秒，拦截{newbie_rule_text}）\n"
        f"自动审核：{'是' if config.auto_moderation_enabled else '否'}\n"
        f"广告检测：{'是' if config.anti_ad_enabled else '否'}\n"
        f"刷屏检测：{'是' if config.anti_spam_enabled else '否'}\n"
        f"默认禁言：{config.default_mute_seconds} 秒\n"
        f"自动撤回：{auto_delete_text}（{auto_delete_categories}）"
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


def format_cached_messages(messages: list[MessageCache]) -> str:
    if not messages:
        return "暂无缓存消息。"
    lines = ["最近消息："]
    for item in messages:
        text = (item.plain_text or "").strip().replace("\n", " ")
        if len(text) > 60:
            text = text[:57] + "..."
        if not text:
            text = "[非文本消息]"
        lines.append(f"#{item.message_id} {item.user_id}: {text}")
    return "\n".join(lines)


def format_cached_message_detail(message: MessageCache | None) -> str:
    if message is None:
        return "没有找到这条缓存消息，可能已过期或不属于本群。"
    text = (message.plain_text or "").strip()
    if not text:
        text = "[非文本消息]"
    return (
        "消息缓存\n"
        f"消息ID：{message.message_id}\n"
        f"群号：{message.group_id}\n"
        f"用户：{message.user_id}\n"
        f"时间：{message.created_at}\n"
        f"图片：{message.image_count}，@：{message.at_count}，链接：{message.link_count}\n"
        f"内容：{text}"
    )
