from enum import IntEnum, StrEnum


class QGuardRole(IntEnum):
    MEMBER = 0
    TRUSTED = 1
    MINI_ADMIN = 2
    GROUP_ADMIN = 3
    GROUP_OWNER = 4
    SUPER_ADMIN = 5


class AuditAction(StrEnum):
    ENABLE_GROUP = "enable_group"
    DISABLE_GROUP = "disable_group"
    WARN = "warn"
    MUTE = "mute"
    UNMUTE = "unmute"
    KICK = "kick"
    KICK_BLACK = "kick_black"
    DELETE_MSG = "delete_msg"
    SET_CARD = "set_card"
    CLEAR_CARD = "clear_card"
    LOCK_CARD = "lock_card"
    UNLOCK_CARD = "unlock_card"
    FIX_CARD = "fix_card"
    SCAN_CARD = "scan_card"
    ADD_RULE = "add_rule"
    DELETE_RULE = "delete_rule"
    HIT_RULE = "hit_rule"
    ADD_SCORE = "add_score"
    RESET_SCORE = "reset_score"
    SCORE_PENALTY = "score_penalty"
    SET_AUTO_DELETE_REPLY = "set_auto_delete_reply"
    SET_ANTI_AD = "set_anti_ad"
    SET_ANTI_SPAM = "set_anti_spam"
    ADD_AD_KEYWORD = "add_ad_keyword"
    REMOVE_AD_KEYWORD = "remove_ad_keyword"
    ADD_WHITELIST = "add_whitelist"
    REMOVE_WHITELIST = "remove_whitelist"
    ADD_BLACKLIST = "add_blacklist"
    REMOVE_BLACKLIST = "remove_blacklist"
    SET_JOIN_REVIEW = "set_join_review"
    SET_JOIN_REVIEW_ANSWER = "set_join_review_answer"
    SET_JOIN_REVIEW_REJECT_REASON = "set_join_review_reject_reason"
    SET_JOIN_WELCOME = "set_join_welcome"
    SET_JOIN_WELCOME_TEMPLATE = "set_join_welcome_template"
    JOIN_WELCOME_SEND = "join_welcome_send"
    JOIN_APPROVE = "join_approve"
    JOIN_REJECT = "join_reject"
    SET_NEWBIE_PROTECTION = "set_newbie_protection"
    SET_NEWBIE_PROTECTION_DURATION = "set_newbie_protection_duration"
    SET_NEWBIE_PROTECTION_LINK = "set_newbie_protection_link"
    SET_NEWBIE_PROTECTION_IMAGE = "set_newbie_protection_image"
    NEWBIE_PROTECTION_HIT = "newbie_protection_hit"
    SET_MEMBER_ROLE = "set_member_role"
    SET_GROUP_NAME = "set_group_name"
    SET_WHOLE_MUTE = "set_whole_mute"
    LOCK_GROUP_NAME = "lock_group_name"
    UNLOCK_GROUP_NAME = "unlock_group_name"
    FIX_GROUP_NAME = "fix_group_name"
    SET_ANONYMOUS = "set_anonymous"
    LOCK_ANONYMOUS = "lock_anonymous"
    UNLOCK_ANONYMOUS = "unlock_anonymous"
    SET_SPECIAL_TITLE = "set_special_title"
    SET_AUTO_PATROL = "set_auto_patrol"
    SET_AUTO_PATROL_INTERVAL = "set_auto_patrol_interval"
    SET_AUTO_CLEANUP = "set_auto_cleanup"
    AUTO_CLEANUP_REMIND = "auto_cleanup_remind"
    AUTO_CLEANUP_KICK = "auto_cleanup_kick"
    SET_PLUGIN_ENABLED = "set_plugin_enabled"
    SET_PLUGIN_PERMISSION = "set_plugin_permission"
    QUERY_PLUGIN_STATUS = "query_plugin_status"
    PATROL = "patrol"
    PERMISSION_DENIED = "permission_denied"
    QUERY_USER = "query_user"


class RuleType(StrEnum):
    KEYWORD = "keyword"
    REGEX = "regex"
    LINK = "link"
    SPAM = "spam"
    CARD_REGEX = "card_regex"


class RuleAction(StrEnum):
    NONE = "none"
    WARN = "warn"
    DELETE = "delete"
    MUTE = "mute"
    KICK = "kick"
    KICK_BLACK = "kick_black"
    FIX_CARD = "fix_card"


class AuditResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
