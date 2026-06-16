import re
from dataclasses import dataclass
from typing import Any

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message


@dataclass(frozen=True)
class TargetParseResult:
    user_id: int
    rest: str


def split_command(prefix: str, text: str) -> list[str]:
    stripped = text.strip()
    if not stripped.startswith(prefix):
        return []
    body = stripped[len(prefix) :].strip()
    return body.split() if body else []


def get_at_user_ids(message: Message) -> list[int]:
    result: list[int] = []
    for segment in message:
        if segment.type == "at":
            qq = segment.data.get("qq")
            if qq and str(qq).isdigit():
                result.append(int(qq))
    return result


def parse_target(event: GroupMessageEvent, args: list[str], target_index: int = 1) -> TargetParseResult | None:
    at_users = get_at_user_ids(event.message)
    rest_args = list(args)
    if at_users:
        if target_index < len(rest_args) and rest_args[target_index].startswith("[CQ:at"):
            rest_args.pop(target_index)
        return TargetParseResult(at_users[0], " ".join(rest_args[target_index:]).strip())

    if target_index >= len(args):
        return None
    token = args[target_index]
    match = re.search(r"\d{5,12}", token)
    if match is None:
        return None
    rest = " ".join(args[target_index + 1 :]).strip()
    return TargetParseResult(int(match.group(0)), rest)


def get_reply_message_id(event: GroupMessageEvent) -> int | None:
    reply: Any = getattr(event, "reply", None)
    message_id = getattr(reply, "message_id", None)
    if isinstance(message_id, int):
        return message_id
    return None


def display_member_name(info: dict[str, Any]) -> str:
    card = str(info.get("card") or "")
    nickname = str(info.get("nickname") or "")
    return card or nickname or str(info.get("user_id", "未知用户"))
