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
    SET_AUTO_DELETE_REPLY = "set_auto_delete_reply"
    ADD_WHITELIST = "add_whitelist"
    REMOVE_WHITELIST = "remove_whitelist"
    ADD_BLACKLIST = "add_blacklist"
    REMOVE_BLACKLIST = "remove_blacklist"
    JOIN_APPROVE = "join_approve"
    JOIN_REJECT = "join_reject"
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
