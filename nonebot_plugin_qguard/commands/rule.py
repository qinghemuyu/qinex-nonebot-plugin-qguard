import re

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole, RuleAction, RuleType
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.rule_repo import RuleRepo
from nonebot_plugin_qguard.services.rule_engine import MessageContext, RuleEngine
from nonebot_plugin_qguard.utils.timeparse import parse_duration

from ._common import ensure_manager, finish_reply, parse_qguard_args

rule_matcher = on_message(priority=5, block=False)


@rule_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    args = parse_qguard_args(event)
    if not args or args[0] != "规则":
        return

    if len(args) < 2:
        await finish_reply(rule_matcher, bot, event, "用法：/管 规则 添加|删除|列表|测试 ...")

    if args[1] == "添加":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN, command_selector=_add_rule_selector(args))
        if denied:
            await finish_reply(rule_matcher, bot, event, denied)
        await _handle_add_rule(bot, event, args)
    elif args[1] == "删除":
        denied = await ensure_manager(bot, event, QGuardRole.GROUP_ADMIN, command_selector="/管 规则 删除 ID[,ID...]")
        if denied:
            await finish_reply(rule_matcher, bot, event, denied)
        await _handle_delete_rule(bot, event, args)
    elif args[1] == "列表":
        denied = await ensure_manager(bot, event, QGuardRole.TRUSTED, command_selector="/管 规则 列表")
        if denied:
            await finish_reply(rule_matcher, bot, event, denied)
        await _handle_list_rules(bot, event)
    elif args[1] == "测试":
        denied = await ensure_manager(bot, event, QGuardRole.TRUSTED, command_selector="/管 规则 测试 文本")
        if denied:
            await finish_reply(rule_matcher, bot, event, denied)
        await _handle_test_rule(bot, event, args)
    else:
        await finish_reply(rule_matcher, bot, event, "未知规则命令。")


async def _handle_add_rule(bot: Bot, event: GroupMessageEvent, args: list[str]) -> None:
    if len(args) < 5:
        await finish_reply(rule_matcher, bot, event, "用法：/管 规则 添加 关键词 xxx 警告")

    try:
        rule_type = _parse_rule_type(args[2])
        action, mute_seconds, delete_message, action_tokens = _parse_rule_action(args[3:])
    except ValueError as exc:
        await finish_reply(rule_matcher, bot, event, str(exc))

    pattern_tokens = args[3 : len(args) - action_tokens]
    pattern = " ".join(pattern_tokens).strip()
    if not pattern:
        await finish_reply(rule_matcher, bot, event, "规则内容不能为空。")
    if rule_type == RuleType.REGEX:
        try:
            re.compile(pattern)
        except re.error as exc:
            await finish_reply(rule_matcher, bot, event, f"正则无效：{exc}")

    async with get_session() as session:
        item = await RuleRepo(session).create(
            group_id=event.group_id,
            rule_type=rule_type,
            pattern=pattern,
            action=action,
            created_by=event.user_id,
            mute_seconds=mute_seconds,
            delete_message=delete_message,
        )
        await AuditLogRepo(session).create(
            group_id=event.group_id,
            operator_id=event.user_id,
            action=AuditAction.ADD_RULE,
            result=AuditResult.SUCCESS,
            related_rule_id=item.id,
            metadata={
                "rule_type": str(rule_type),
                "pattern": pattern,
                "action": str(action),
                "mute_seconds": mute_seconds,
                "delete_message": delete_message,
            },
        )
        await session.commit()
    await finish_reply(rule_matcher, bot, event, f"规则已添加：#{item.id}")


async def _handle_delete_rule(bot: Bot, event: GroupMessageEvent, args: list[str]) -> None:
    if len(args) < 3:
        await finish_reply(rule_matcher, bot, event, "用法：/管 规则 删除 ID[,ID...]")
    try:
        rule_ids = _parse_rule_ids(args[2:])
    except ValueError as exc:
        await finish_reply(rule_matcher, bot, event, str(exc))
    if not rule_ids:
        await finish_reply(rule_matcher, bot, event, "用法：/管 规则 删除 ID[,ID...]")

    deleted: list[int] = []
    missing: list[int] = []
    async with get_session() as session:
        repo = RuleRepo(session)
        audit_repo = AuditLogRepo(session)
        for rule_id in rule_ids:
            item = await repo.disable(rule_id, event.group_id)
            if item is None:
                missing.append(rule_id)
            else:
                deleted.append(rule_id)
            await audit_repo.create(
                group_id=event.group_id,
                operator_id=event.user_id,
                action=AuditAction.DELETE_RULE,
                result=AuditResult.SUCCESS if item else AuditResult.SKIPPED,
                related_rule_id=rule_id,
            )
        await session.commit()

    if len(rule_ids) == 1:
        if not deleted:
            await finish_reply(rule_matcher, bot, event, "没有找到这条规则。")
        await finish_reply(rule_matcher, bot, event, f"规则 #{deleted[0]} 已删除。")

    lines = ["批量删除规则完成："]
    if deleted:
        lines.append("已删除：" + "、".join(f"#{rule_id}" for rule_id in deleted))
    if missing:
        lines.append("未找到：" + "、".join(f"#{rule_id}" for rule_id in missing))
    await finish_reply(rule_matcher, bot, event, "\n".join(lines))


async def _handle_list_rules(bot: Bot, event: GroupMessageEvent) -> None:
    async with get_session() as session:
        rules = await RuleRepo(session).list_all(event.group_id, limit=20)
    if not rules:
        await finish_reply(rule_matcher, bot, event, "当前没有规则。")
    lines = ["规则列表："]
    for item in rules:
        status = "启用" if item.enabled else "停用"
        extra = f" {item.mute_seconds}s" if item.mute_seconds else ""
        score = item.score_delta if item.score_delta > 0 else 1
        lines.append(f"#{item.id} [{status}] {item.rule_type} {item.action}{extra} +{score}分: {item.pattern}")
    await finish_reply(rule_matcher, bot, event, "\n".join(lines))


async def _handle_test_rule(bot: Bot, event: GroupMessageEvent, args: list[str]) -> None:
    if len(args) < 3:
        await finish_reply(rule_matcher, bot, event, "用法：/管 规则 测试 文本")
    text = " ".join(args[2:]).strip()
    decision = await RuleEngine().check(
        MessageContext(
            group_id=event.group_id,
            user_id=event.user_id,
            message_id=event.message_id,
            plain_text=text,
            raw_message=text,
        )
    )
    if not decision.hit:
        await finish_reply(rule_matcher, bot, event, "未命中规则。")
    await finish_reply(
        rule_matcher,
        bot,
        event,
        f"命中规则 #{decision.rule_id}，动作：{decision.action}"
        + (f"，禁言 {decision.mute_seconds} 秒" if decision.mute_seconds else "")
        + f"，积分 +{decision.score_delta}"
    )


def _parse_rule_type(text: str) -> RuleType:
    if text in {"关键词", "关键字", "keyword"}:
        return RuleType.KEYWORD
    if text in {"正则", "regex"}:
        return RuleType.REGEX
    raise ValueError("规则类型只支持：关键词、正则。")


def _add_rule_selector(args: list[str]) -> str:
    action_text = " ".join(args[3:])
    if "踢黑" in action_text:
        return "/管 规则 添加 正则 xxx 踢出"
    if "踢出" in action_text or "踢" in action_text:
        return "/管 规则 添加 正则 xxx 踢出"
    if "禁言" in action_text:
        return "/管 规则 添加 关键词 xxx 禁言10m"
    if "撤回" in action_text or "删除" in action_text:
        return "/管 规则 添加 关键词 xxx 撤回"
    return "/管 规则 添加 关键词 xxx 警告"


def _parse_rule_ids(tokens: list[str]) -> list[int]:
    raw = " ".join(tokens).strip()
    if not raw:
        return []
    result: list[int] = []
    seen: set[int] = set()
    for item in re.split(r"[\s,，、;；]+", raw):
        item = item.strip().removeprefix("#")
        if not item:
            continue
        if not item.isdigit():
            raise ValueError("规则 ID 只能是数字，多个 ID 可用逗号或空格分隔。")
        rule_id = int(item)
        if rule_id not in seen:
            seen.add(rule_id)
            result.append(rule_id)
    return result


def _parse_rule_action(tokens: list[str]) -> tuple[RuleAction, int, bool, int]:
    if not tokens:
        raise ValueError("缺少规则动作。")
    last = tokens[-1]
    if last in {"警告", "warn"}:
        return RuleAction.WARN, 0, False, 1
    if last in {"撤回", "删除", "delete"}:
        return RuleAction.DELETE, 0, True, 1
    if last in {"踢出", "踢", "kick"}:
        return RuleAction.KICK, 0, True, 1
    if last in {"踢黑", "kick_black"}:
        return RuleAction.KICK_BLACK, 0, True, 1
    if last.startswith("禁言"):
        duration_text = last.removeprefix("禁言") or "10m"
        return RuleAction.MUTE, parse_duration(duration_text), True, 1
    if len(tokens) >= 2 and tokens[-2] == "禁言":
        return RuleAction.MUTE, parse_duration(tokens[-1]), True, 2
    raise ValueError("规则动作只支持：警告、撤回、禁言10m、踢出。")
