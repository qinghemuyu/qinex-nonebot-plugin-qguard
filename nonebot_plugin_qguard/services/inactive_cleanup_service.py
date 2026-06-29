from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Any

from nonebot.adapters.onebot.v11 import Bot

from nonebot_plugin_qguard.adapter.onebot_v11_ops import OneBotV11GroupOps
from nonebot_plugin_qguard.config import load_config
from nonebot_plugin_qguard.enums import AuditAction, AuditResult, QGuardRole
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.models.member_profile import MemberProfile
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.repositories.group_config_repo import GroupConfigRepo
from nonebot_plugin_qguard.repositories.member_cleanup_notice_repo import MemberCleanupNoticeRepo
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo
from nonebot_plugin_qguard.repositories.whitelist_repo import WhitelistRepo
from nonebot_plugin_qguard.services.permission_service import PermissionService
from nonebot_plugin_qguard.services.result import ActionResult
from nonebot_plugin_qguard.utils.timeparse import parse_duration

DEFAULT_CLEANUP_REMINDER_DAYS = (30, 60)
DEFAULT_CLEANUP_KICK_DAYS = 90
DEFAULT_CLEANUP_INTERVAL_SECONDS = 86400
MIN_CLEANUP_INTERVAL_SECONDS = 60


@dataclass(frozen=True)
class InactiveCleanupRunResult:
    checked: int = 0
    reminded: int = 0
    pending: int = 0
    kicked: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def message(self) -> str:
        return (
            "自动清理完成："
            f"检查 {self.checked} 人，提醒 {self.reminded} 人，待主人确认 {self.pending} 人，踢出 {self.kicked} 人，"
            f"跳过 {self.skipped} 人，失败 {self.failed} 人。"
        )


@dataclass(frozen=True)
class PendingCleanupMember:
    user_id: int
    inactive_days: int
    pending_at: datetime | None


@dataclass(frozen=True)
class InactiveCleanupConfirmResult:
    total: int = 0
    kicked: int = 0
    kept: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def message(self) -> str:
        return (
            "自动清理确认完成："
            f"待确认 {self.total} 人，踢出 {self.kicked} 人，保留 {self.kept} 人，"
            f"跳过 {self.skipped} 人，失败 {self.failed} 人。"
        )


@dataclass(frozen=True)
class InactiveCleanupCancelResult:
    cleared: int = 0

    @property
    def message(self) -> str:
        return f"已取消 {self.cleared} 条自动清理待确认记录。"


def serialize_cleanup_reminder_days(days: list[int] | tuple[int, ...] | set[int]) -> str:
    return ",".join(str(day) for day in sorted({day for day in days if day > 0}))


def deserialize_cleanup_reminder_days(raw: str | None) -> list[int]:
    if raw is None:
        return list(DEFAULT_CLEANUP_REMINDER_DAYS)
    values: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            day = int(item)
        except ValueError:
            continue
        if day > 0:
            values.append(day)
    return sorted(set(values))


def format_cleanup_reminder_days(days: list[int] | tuple[int, ...] | set[int]) -> str:
    ordered = sorted({day for day in days if day > 0})
    if not ordered:
        return "关闭"
    return "、".join(f"{day}天" for day in ordered)


def parse_cleanup_day_token(text: str) -> int:
    value = text.strip().lower()
    if value.isdigit():
        day = int(value)
    else:
        seconds = parse_duration(value)
        day = ceil(seconds / 86400)
    if day <= 0:
        raise ValueError("天数必须大于 0。")
    return day


class InactiveCleanupService:
    async def status(self, group_id: int):
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            await session.commit()
            return config

    async def set_enabled(self, group_id: int, operator_id: int, enabled: bool) -> ActionResult:
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_auto_cleanup_enabled(group_id, enabled)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_CLEANUP,
                result=AuditResult.SUCCESS,
                metadata={"auto_cleanup_enabled": enabled},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_CLEANUP),
                message=f"自动清理已{'开启' if config.auto_cleanup_enabled else '关闭'}。",
            )

    async def set_interval_seconds(self, group_id: int, operator_id: int, seconds: int) -> ActionResult:
        seconds = max(MIN_CLEANUP_INTERVAL_SECONDS, seconds)
        async with get_session() as session:
            config = await GroupConfigRepo(session).set_auto_cleanup_interval_seconds(group_id, seconds)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_CLEANUP,
                result=AuditResult.SUCCESS,
                metadata={"auto_cleanup_interval_seconds": seconds},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_CLEANUP),
                message=f"自动清理扫描间隔已设置为 {config.auto_cleanup_interval_seconds} 秒。",
            )

    async def set_reminder_days(self, group_id: int, operator_id: int, days: list[int]) -> ActionResult:
        days = sorted({day for day in days if day > 0})
        async with get_session() as session:
            config = await GroupConfigRepo(session).get_or_create(group_id)
            days = [day for day in days if day < config.auto_cleanup_kick_days]
            config = await GroupConfigRepo(session).set_auto_cleanup_reminder_days(
                group_id,
                serialize_cleanup_reminder_days(days),
            )
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_CLEANUP,
                result=AuditResult.SUCCESS,
                metadata={"auto_cleanup_reminder_days": days},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_CLEANUP),
                message=f"自动清理提醒档位已设置为：{format_cleanup_reminder_days(days)}。",
            )

    async def set_kick_days(self, group_id: int, operator_id: int, days: int) -> ActionResult:
        days = max(1, days)
        async with get_session() as session:
            repo = GroupConfigRepo(session)
            config = await repo.get_or_create(group_id)
            reminder_days = [day for day in deserialize_cleanup_reminder_days(config.auto_cleanup_reminder_days) if day < days]
            config = await repo.set_auto_cleanup_kick_days(group_id, days)
            await repo.set_auto_cleanup_reminder_days(group_id, serialize_cleanup_reminder_days(reminder_days))
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.SET_AUTO_CLEANUP,
                result=AuditResult.SUCCESS,
                metadata={"auto_cleanup_kick_days": days, "auto_cleanup_reminder_days": reminder_days},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.SET_AUTO_CLEANUP),
                message=(
                    f"自动清理踢出阈值已设置为 {config.auto_cleanup_kick_days} 天；"
                    f"提醒档位：{format_cleanup_reminder_days(reminder_days)}。"
                ),
            )

    async def run_group(
        self,
        bot: Bot,
        group_id: int,
        *,
        operator_id: int | None = None,
        now: datetime | None = None,
        notify_owners: bool = True,
    ) -> InactiveCleanupRunResult:
        now = now or datetime.utcnow()
        ops = OneBotV11GroupOps(bot)
        bot_id = _bot_id(bot)

        async with get_session() as session:
            config_repo = GroupConfigRepo(session)
            config = await config_repo.get_or_create(group_id)
            if not config.enabled or not config.auto_cleanup_enabled:
                return InactiveCleanupRunResult()

            reminder_days = deserialize_cleanup_reminder_days(config.auto_cleanup_reminder_days)
            kick_days = max(1, config.auto_cleanup_kick_days)
            member_profiles = {
                profile.user_id: profile
                for profile in await MemberRepo(session).list_by_group(group_id)
            }
            try:
                group_members = await ops.get_group_member_list(group_id)
            except Exception as exc:
                await AuditLogRepo(session).create(
                    group_id=group_id,
                    operator_id=operator_id or bot_id,
                    action=AuditAction.AUTO_CLEANUP_REMIND,
                    result=AuditResult.FAILED,
                    error_message=str(exc),
                    metadata={"stage": "get_group_member_list"},
                )
                await session.commit()
                return InactiveCleanupRunResult(failed=1)

            notice_repo = MemberCleanupNoticeRepo(session)
            audit_repo = AuditLogRepo(session)
            permission = PermissionService(session)
            whitelist_repo = WhitelistRepo(session)
            checked = reminded = pending = kicked = skipped = failed = 0

            for member in group_members:
                user_id = _int_or_none(member.get("user_id"))
                if user_id is None or user_id == bot_id:
                    skipped += 1
                    continue
                checked += 1

                profile = member_profiles.get(user_id)
                last_active_at = _member_last_active(member, profile)
                if last_active_at is None:
                    skipped += 1
                    continue
                inactive_days = max(0, (now - last_active_at).days)
                if inactive_days < min([kick_days, *reminder_days] or [kick_days]):
                    continue

                if await whitelist_repo.is_whitelisted(group_id, user_id):
                    skipped += 1
                    continue
                role = await permission.get_role(ops, group_id, user_id, member_info=member)
                if role >= QGuardRole.TRUSTED:
                    skipped += 1
                    continue

                notice = await notice_repo.get(group_id, user_id)
                if inactive_days >= kick_days:
                    if notice is not None and notice.kicked_at is not None:
                        skipped += 1
                        continue
                    item, created = await notice_repo.mark_pending_cleanup(
                        group_id,
                        user_id,
                        inactive_days=inactive_days,
                        when=now,
                    )
                    if created:
                        await audit_repo.create(
                            group_id=group_id,
                            operator_id=operator_id or bot_id,
                            target_user_id=user_id,
                            action=AuditAction.AUTO_CLEANUP_PENDING,
                            result=AuditResult.SUCCESS,
                            reason=f"{inactive_days} 天未发言，已加入自动清理待确认。",
                            metadata={"inactive_days": inactive_days, "kick_days": kick_days},
                        )
                        pending += 1
                    else:
                        skipped += 1
                    continue

                threshold_days = _matched_reminder_threshold(inactive_days, reminder_days)
                if threshold_days is None:
                    continue
                last_reminded_days = 0 if notice is None else notice.last_reminded_days
                if last_reminded_days >= threshold_days:
                    continue
                try:
                    await _send_private_reminder(bot, group_id, user_id, inactive_days, kick_days)
                    await notice_repo.mark_reminded(group_id, user_id, threshold_days=threshold_days, when=now)
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id or bot_id,
                        target_user_id=user_id,
                        action=AuditAction.AUTO_CLEANUP_REMIND,
                        result=AuditResult.SUCCESS,
                        reason=f"{inactive_days} 天未发言，已私聊提醒。",
                        metadata={"inactive_days": inactive_days, "threshold_days": threshold_days},
                    )
                    reminded += 1
                except Exception as exc:
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id or bot_id,
                        target_user_id=user_id,
                        action=AuditAction.AUTO_CLEANUP_REMIND,
                        result=AuditResult.FAILED,
                        reason=f"{inactive_days} 天未发言，私聊提醒失败。",
                        error_message=str(exc),
                        metadata={"inactive_days": inactive_days, "threshold_days": threshold_days},
                    )
                    failed += 1

            await config_repo.mark_auto_cleanup_ran(group_id, now)
            await session.commit()
            result = InactiveCleanupRunResult(
                checked=checked,
                reminded=reminded,
                pending=pending,
                kicked=kicked,
                skipped=skipped,
                failed=failed,
            )
        if notify_owners and result.pending > 0 and operator_id is None:
            await _notify_cleanup_pending(bot, group_id, result.pending, kick_days)
        return result

    async def list_pending(self, group_id: int, limit: int = 20) -> list[PendingCleanupMember]:
        async with get_session() as session:
            items = await MemberCleanupNoticeRepo(session).list_pending_cleanup(group_id, limit=limit)
        return [
            PendingCleanupMember(
                user_id=item.user_id,
                inactive_days=item.pending_cleanup_inactive_days,
                pending_at=item.pending_cleanup_at,
            )
            for item in items
        ]

    async def keep_members(
        self,
        group_id: int,
        operator_id: int,
        user_ids: list[int],
        *,
        reason: str | None = None,
    ) -> InactiveCleanupCancelResult:
        unique_user_ids = sorted({user_id for user_id in user_ids if user_id > 0})
        if not unique_user_ids:
            return InactiveCleanupCancelResult()
        async with get_session() as session:
            whitelist_repo = WhitelistRepo(session)
            notice_repo = MemberCleanupNoticeRepo(session)
            audit_repo = AuditLogRepo(session)
            cleared = 0
            keep_reason = reason or "自动清理保留"
            for user_id in unique_user_ids:
                await whitelist_repo.add(group_id, user_id, operator_id, keep_reason)
                if await notice_repo.clear_pending_cleanup(group_id, user_id):
                    cleared += 1
                await audit_repo.create(
                    group_id=group_id,
                    operator_id=operator_id,
                    target_user_id=user_id,
                    action=AuditAction.ADD_WHITELIST,
                    result=AuditResult.SUCCESS,
                    reason=keep_reason,
                    metadata={"source": "auto_cleanup_keep"},
                )
            await session.commit()
        return InactiveCleanupCancelResult(cleared=cleared)

    async def cancel_pending(
        self,
        group_id: int,
        operator_id: int,
        user_ids: list[int] | None = None,
    ) -> InactiveCleanupCancelResult:
        async with get_session() as session:
            notice_repo = MemberCleanupNoticeRepo(session)
            audit_repo = AuditLogRepo(session)
            if user_ids:
                candidates = [item for item in await notice_repo.list_pending_cleanup(group_id, limit=500) if item.user_id in set(user_ids)]
            else:
                candidates = await notice_repo.list_pending_cleanup(group_id, limit=500)
            cleared = 0
            for item in candidates:
                if await notice_repo.clear_pending_cleanup(group_id, item.user_id):
                    cleared += 1
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=item.user_id,
                        action=AuditAction.AUTO_CLEANUP_CANCEL,
                        result=AuditResult.SUCCESS,
                        reason="取消自动清理待确认。",
                    )
            await session.commit()
        return InactiveCleanupCancelResult(cleared=cleared)

    async def confirm_pending(
        self,
        bot: Bot,
        group_id: int,
        *,
        operator_id: int,
        exclude_user_ids: list[int] | None = None,
        now: datetime | None = None,
    ) -> InactiveCleanupConfirmResult:
        now = now or datetime.utcnow()
        ops = OneBotV11GroupOps(bot)
        exclude = {user_id for user_id in (exclude_user_ids or []) if user_id > 0}
        async with get_session() as session:
            notice_repo = MemberCleanupNoticeRepo(session)
            audit_repo = AuditLogRepo(session)
            profile_repo = MemberRepo(session)
            whitelist_repo = WhitelistRepo(session)
            permission = PermissionService(session)
            candidates = await notice_repo.list_pending_cleanup(group_id, limit=500)
            total = len(candidates)
            kicked = kept = skipped = failed = 0
            for item in candidates:
                user_id = item.user_id
                inactive_days = item.pending_cleanup_inactive_days
                if user_id in exclude:
                    await whitelist_repo.add(group_id, user_id, operator_id, "自动清理确认时保留")
                    await notice_repo.clear_pending_cleanup(group_id, user_id)
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.ADD_WHITELIST,
                        result=AuditResult.SUCCESS,
                        reason="自动清理确认时保留。",
                        metadata={"source": "auto_cleanup_confirm_exclude", "inactive_days": inactive_days},
                    )
                    kept += 1
                    continue
                if await whitelist_repo.is_whitelisted(group_id, user_id):
                    await notice_repo.clear_pending_cleanup(group_id, user_id)
                    skipped += 1
                    continue
                try:
                    member_info = await ops.get_group_member_info(group_id, user_id)
                    role = await permission.get_role(ops, group_id, user_id, member_info=member_info)
                    if role >= QGuardRole.TRUSTED:
                        await notice_repo.clear_pending_cleanup(group_id, user_id)
                        skipped += 1
                        continue
                    await ops.kick(group_id, user_id, reject_add_request=False)
                    await profile_repo.add_kick(group_id, user_id)
                    await notice_repo.mark_kicked(group_id, user_id, when=now)
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.AUTO_CLEANUP_KICK,
                        result=AuditResult.SUCCESS,
                        reason=f"{inactive_days} 天未发言，经主人确认后自动清理踢出，不加入黑名单。",
                        metadata={"inactive_days": inactive_days},
                    )
                    kicked += 1
                except Exception as exc:
                    await audit_repo.create(
                        group_id=group_id,
                        operator_id=operator_id,
                        target_user_id=user_id,
                        action=AuditAction.AUTO_CLEANUP_KICK,
                        result=AuditResult.FAILED,
                        reason=f"{inactive_days} 天未发言，主人确认后自动清理踢出失败。",
                        error_message=str(exc),
                        metadata={"inactive_days": inactive_days},
                    )
                    failed += 1
            await session.commit()
        return InactiveCleanupConfirmResult(total=total, kicked=kicked, kept=kept, skipped=skipped, failed=failed)


def _matched_reminder_threshold(inactive_days: int, reminder_days: list[int]) -> int | None:
    matched = [day for day in reminder_days if inactive_days >= day]
    if not matched:
        return None
    return max(matched)


def _member_last_active(member: dict[str, Any], profile: MemberProfile | None) -> datetime | None:
    last_sent_time = _int_or_none(member.get("last_sent_time"))
    if last_sent_time and last_sent_time > 0:
        return datetime.utcfromtimestamp(last_sent_time)
    if profile is not None and profile.last_active_at is not None:
        return profile.last_active_at
    join_time = _int_or_none(member.get("join_time"))
    if join_time and join_time > 0:
        return datetime.utcfromtimestamp(join_time)
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bot_id(bot: Bot) -> int:
    try:
        return int(bot.self_id)
    except (TypeError, ValueError):
        return 0


async def _send_private_reminder(bot: Bot, group_id: int, user_id: int, inactive_days: int, kick_days: int) -> None:
    message = (
        f"你已经在群 {group_id} 里 {inactive_days} 天没有发言啦。\n"
        f"本群开启了长期未活跃自动清理，达到 {kick_days} 天会进入待确认清单，主人确认后才会被移出群聊。\n"
        "自动清理不会加入黑名单。\n"
        "如果还需要留在群里，回群里说句话就会刷新活跃时间。"
    )
    if hasattr(bot, "send_private_msg"):
        await bot.send_private_msg(user_id=user_id, message=message)
        return
    await bot.call_api("send_private_msg", user_id=user_id, message=message)


async def _notify_cleanup_pending(bot: Bot, group_id: int, pending_count: int, kick_days: int) -> None:
    try:
        owner_ids = load_config().qguard_super_admins
    except Exception:
        owner_ids = set()
    if not owner_ids:
        return

    message = (
        "QGuard 自动清理待确认\n"
        f"群：{group_id}\n"
        f"新增待确认：{pending_count} 人\n"
        f"阈值：{kick_days} 天未发言\n"
        "请在群内使用 /管 自动清理 待确认 查看。\n"
        "确认踢出：/管 自动清理 确认\n"
        "保留成员：/管 自动清理 保留 QQ 原因\n"
        "临时排除：/管 自动清理 确认 排除 QQ"
    )
    for owner_id in owner_ids:
        try:
            if hasattr(bot, "send_private_msg"):
                await bot.send_private_msg(user_id=owner_id, message=message)
            else:
                await bot.call_api("send_private_msg", user_id=owner_id, message=message)
        except Exception:
            continue
