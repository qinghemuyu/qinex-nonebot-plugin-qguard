import re
from typing import Any

from pydantic import BaseModel

from nonebot_plugin_qguard.enums import RuleType
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.ad_keyword_repo import AdKeywordRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.rule_repo import RuleRepo
from nonebot_plugin_qguard.services.anti_ad_service import AntiAdService
from nonebot_plugin_qguard.services.anti_spam_service import AntiSpamService


class MessageContext(BaseModel):
    group_id: int
    user_id: int
    message_id: int
    plain_text: str
    raw_message: Any
    image_count: int = 0
    at_count: int = 0
    link_count: int = 0
    is_new_member: bool = False


class ModerationDecision(BaseModel):
    hit: bool
    rule_id: int | None = None
    rule_type: str | None = None
    action: str = "none"
    reason: str = ""
    score_delta: int = 0
    mute_seconds: int = 0
    delete_message: bool = False


class RuleEngine:
    async def check(self, context: MessageContext) -> ModerationDecision:
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(context.group_id)
            if not config.enabled or not config.auto_moderation_enabled:
                return ModerationDecision(hit=False)
            anti_ad_enabled = config.anti_ad_enabled
            anti_spam_enabled = config.anti_spam_enabled
            keyword_check_enabled = config.keyword_check_enabled
            ad_keywords = (
                [item.keyword for item in await AdKeywordRepo(session).list_enabled(context.group_id)]
                if anti_ad_enabled
                else []
            )
            rules = await RuleRepo(session).list_enabled(context.group_id)

        if anti_ad_enabled:
            anti_ad = AntiAdService().check(
                context.plain_text,
                context.link_count,
                context.at_count,
                ad_keywords,
            )
            if anti_ad is not None:
                return ModerationDecision(hit=True, **anti_ad)

        if anti_spam_enabled:
            anti_spam = AntiSpamService().check(context.group_id, context.user_id, context.plain_text)
            if anti_spam is not None:
                return ModerationDecision(hit=True, **anti_spam)

        if not keyword_check_enabled:
            return ModerationDecision(hit=False)

        for rule in rules:
            if rule.rule_type == str(RuleType.KEYWORD):
                matched = rule.pattern in context.plain_text
            elif rule.rule_type == str(RuleType.REGEX):
                try:
                    matched = re.search(rule.pattern, context.plain_text, re.IGNORECASE) is not None
                except re.error:
                    matched = False
            else:
                matched = False

            if matched:
                return ModerationDecision(
                    hit=True,
                    rule_id=rule.id,
                    rule_type=rule.rule_type,
                    action=rule.action,
                    reason=f"命中规则 #{rule.id}: {rule.pattern}",
                    score_delta=rule.score_delta if rule.score_delta > 0 else 1,
                    mute_seconds=rule.mute_seconds,
                    delete_message=rule.delete_message,
                )
        return ModerationDecision(hit=False)
