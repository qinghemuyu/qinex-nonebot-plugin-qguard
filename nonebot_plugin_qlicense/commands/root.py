from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from nonebot_plugin_qlicense.config import load_config
from nonebot_plugin_qlicense.services.license_client import LicenseAPIError
from nonebot_plugin_qlicense.services.license_service import (
    MAC_SOURCE_TIP,
    LicenseBotService,
    extract_mac,
    extract_qq,
    parse_quota_args,
)

from ._common import check_qguard_command_permission, extract_at_qq, finish_reply, get_event_group_id, parse_license_command

license_matcher = on_message(priority=5, block=False)

HELP_TEXT = f"""QLicense 命令
/激活 S3 MAC
/激活 P4 MAC
/激活 状态
/授权 查询 QQ
/授权 配额 QQ 数量 [S3|P4]
/授权 默认配额 数量 [S3|P4]
/授权 解绑 MAC
/授权 禁用 MAC
/授权 恢复 MAC
/授权 预检 [S3|P4] MAC
/授权 同步预览
/授权 同步执行

{MAC_SOURCE_TIP}
"""


@license_matcher.handle()
async def _(bot: Bot, event: MessageEvent) -> None:
    parsed = parse_license_command(event.get_plaintext())
    if parsed is None:
        return
    command, actions, args_text = parsed
    action = actions[0] if actions else "帮助"
    config = load_config()
    service = LicenseBotService(config)

    permission = await check_qguard_command_permission(
        bot,
        event,
        selector=_permission_selector(command, action),
        fallback_role=_fallback_role(command, action),
        enforce_plugin_enabled=action != "开启",
    )
    if permission.denied_reason:
        await finish_reply(license_matcher, bot, event, permission.denied_reason)
    if command == "/授权" and not permission.checked and int(event.user_id) not in config.qlicense_super_admins:
        await finish_reply(license_matcher, bot, event, "权限不足，只有主人可以管理授权。")

    try:
        if command == "/激活":
            await _handle_activate(bot, event, service, action, args_text)
        if command == "/授权":
            await _handle_admin(bot, event, service, action, args_text)
    except LicenseAPIError as exc:
        await finish_reply(license_matcher, bot, event, f"授权服务请求失败：{exc.message}\n{MAC_SOURCE_TIP}")

    await finish_reply(license_matcher, bot, event, HELP_TEXT)


async def _handle_activate(bot: Bot, event: MessageEvent, service: LicenseBotService, action: str, args_text: str) -> None:
    if action in {"帮助", "help"}:
        await finish_reply(license_matcher, bot, event, HELP_TEXT)
    if action == "状态":
        await finish_reply(license_matcher, bot, event, await service.account_status(event.user_id))
    prod = action.upper()
    if prod not in {"S3", "P4"}:
        await finish_reply(license_matcher, bot, event, "用法：/激活 S3 MAC 或 /激活 P4 MAC")
    mac = extract_mac(args_text)
    if not mac:
        await finish_reply(license_matcher, bot, event, f"用法：/激活 {prod} MAC\n{MAC_SOURCE_TIP}")
    binder = service.bind_p4 if prod == "P4" else service.bind_s3
    await finish_reply(
        license_matcher,
        bot,
        event,
        await binder(
            qq=event.user_id,
            mac=mac,
            group_id=get_event_group_id(event),
            operator_id=event.user_id,
        ),
    )


async def _handle_admin(bot: Bot, event: MessageEvent, service: LicenseBotService, action: str, args_text: str) -> None:
    if action in {"帮助", "help"}:
        await finish_reply(license_matcher, bot, event, HELP_TEXT)
    if action == "查询":
        qq = extract_at_qq(event) or extract_qq(args_text)
        if not qq:
            await finish_reply(license_matcher, bot, event, "用法：/授权 查询 QQ")
        await finish_reply(license_matcher, bot, event, await service.account_status(qq))
    if action == "配额":
        raw = (extract_at_qq(event) + " " + args_text).strip() if extract_at_qq(event) else args_text
        parsed = parse_quota_args(raw)
        if parsed is None:
            await finish_reply(license_matcher, bot, event, "用法：/授权 配额 QQ 数量 [S3|P4]，例如 /授权 配额 1348984838 2 P4")
        qq, quota = parsed
        product = "p4" if "P4" in raw.upper() else "s3"
        await finish_reply(license_matcher, bot, event, await service.set_quota(qq=qq, quota_total=quota, operator_id=event.user_id, product=product))
    if action == "默认配额":
        quota = _parse_first_int(args_text)
        if quota is None:
            await finish_reply(license_matcher, bot, event, "用法：/授权 默认配额 数量 [S3|P4]，例如 /授权 默认配额 1 P4")
        product = "p4" if "P4" in args_text.upper() else "s3"
        await finish_reply(license_matcher, bot, event, await service.set_default_quota(quota_total=quota, operator_id=event.user_id, product=product))
    if action in {"解绑", "禁用", "恢复"}:
        mac = extract_mac(args_text)
        if not mac:
            await finish_reply(license_matcher, bot, event, f"用法：/授权 {action} MAC")
        await finish_reply(license_matcher, bot, event, await service.change_device(mac=mac, action=action, operator_id=event.user_id))
    if action == "预检":
        mac = extract_mac(args_text)
        if not mac:
            await finish_reply(license_matcher, bot, event, "用法：/授权 预检 [S3|P4] MAC")
        product = "p4" if "P4" in args_text.upper() else "s3"
        await finish_reply(license_matcher, bot, event, await service.check_device_text(mac=mac, product=product))
    if action == "同步预览":
        await finish_reply(license_matcher, bot, event, await service.legacy_sync(execute=False, operator_id=event.user_id))
    if action == "同步执行":
        await finish_reply(license_matcher, bot, event, await service.legacy_sync(execute=True, operator_id=event.user_id))


def _permission_selector(command: str, action: str) -> str:
    if action in {"帮助", "help"}:
        return command
    return f"{command} {action}"


def _fallback_role(command: str, action: str) -> int:
    if command == "/激活":
        return 0
    return 5


def _parse_first_int(text: str) -> int | None:
    for item in text.split():
        try:
            return max(0, int(item))
        except ValueError:
            continue
    return None
