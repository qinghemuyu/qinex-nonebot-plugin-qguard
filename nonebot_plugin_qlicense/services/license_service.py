from __future__ import annotations

import re

from nonebot_plugin_qlicense.config import Config, load_config
from nonebot_plugin_qlicense.services.license_client import LicenseAPIError, LicenseClient

MAC_SOURCE_TIP = "MAC 必须从板子专属配置页面复制，别用电脑网卡、路由器列表或手机蓝牙里的 MAC。"


class LicenseBotService:
    def __init__(self, config: Config | None = None, client: LicenseClient | None = None) -> None:
        self.config = config or _safe_load_config()
        self.client = client or LicenseClient(self.config)

    async def bind_s3(self, *, qq: int, mac: str, group_id: int | None, operator_id: int | None) -> str:
        data = await self.client.post(
            "/internal/bot/s3/bind",
            {
                "qq": str(qq),
                "mac": mac,
                "group_id": group_id,
                "operator_id": operator_id,
                "remark": "QQ 机器人自助登记",
            },
        )
        try:
            preflight = await self.check_device(mac=mac, product="s3")
        except LicenseAPIError as exc:
            raise LicenseAPIError(
                f"S3 已登记，但在线激活预检失败：{exc.message}",
                data=exc.data or data,
                status_code=exc.status_code,
            ) from exc
        if not preflight.get("authorized"):
            raise LicenseAPIError(
                f"S3 已登记，但在线激活预检未通过：{preflight.get('message', '未知原因')}",
                data=preflight,
                status_code=409,
            )
        data["activation_ready"] = True
        data["preflight"] = preflight
        return format_bind_result(data)

    async def account_status(self, qq: int | str) -> str:
        data = await self.client.post("/internal/bot/account/status", {"qq": str(qq)})
        return format_account_status(data)

    async def set_quota(self, *, qq: int | str, quota_total: int, operator_id: int | None) -> str:
        data = await self.client.post(
            "/internal/bot/quota/set",
            {
                "qq": str(qq),
                "product": "s3",
                "quota_total": quota_total,
                "operator_id": operator_id,
                "remark": "QQ 机器人设置",
            },
        )
        return "S3 配额已更新。\n" + format_account_status(data)

    async def set_default_quota(self, *, quota_total: int, operator_id: int | None) -> str:
        data = await self.client.post(
            "/internal/bot/default-quota/set",
            {"product": "s3", "quota_total": quota_total, "operator_id": operator_id},
        )
        return f"全局默认 S3 配额已设置为 {data.get('default_quota', quota_total)}。"

    async def change_device(self, *, mac: str, action: str, operator_id: int | None) -> str:
        path_map = {
            "解绑": "/internal/bot/device/unbind",
            "禁用": "/internal/bot/device/disable",
            "恢复": "/internal/bot/device/enable",
        }
        data = await self.client.post(path_map[action], {"mac": mac, "operator_id": operator_id})
        action_label = {"解绑": "解绑", "禁用": "禁用", "恢复": "恢复"}[action]
        return f"设备已{action_label}：{data.get('mac', '')}"

    async def check_device(self, *, mac: str, product: str = "s3") -> dict:
        data = await self.client.post("/internal/bot/device/check", {"mac": mac, "product": product})
        data.setdefault("message", "在线激活预检通过")
        return data

    async def check_device_text(self, *, mac: str, product: str = "s3") -> str:
        data = await self.check_device(mac=mac, product=product)
        return format_device_check(data)

    async def legacy_sync(self, *, execute: bool, operator_id: int | None) -> str:
        data = await self.client.post(
            "/internal/bot/legacy-sync",
            {"execute": execute, "operator_id": operator_id},
        )
        title = "历史授权同步执行结果" if execute else "历史授权同步预览"
        return (
            f"{title}\n"
            f"设备总数：{data.get('total_devices', 0)}\n"
            f"可解析 QQ：{data.get('parsed', 0)}\n"
            f"跳过：{data.get('skipped', 0)}\n"
            f"新增绑定：{data.get('created_bindings', 0)}\n"
            f"已有绑定：{data.get('skipped_existing', 0)}\n"
            f"更新配额：{data.get('updated_accounts', 0)}\n"
            f"冲突：{data.get('conflicts', 0)}"
        )


def format_bind_result(data: dict) -> str:
    prefix = "这块 S3 已经登记过。" if data.get("already_bound") else "S3 板子已登记。"
    ready = "通过" if data.get("activation_ready") else "未确认"
    return (
        f"{prefix}\n"
        f"设备：{data.get('mac', '')}\n"
        f"额度：{data.get('used', 0)}/{data.get('quota_total', 0)}\n"
        f"在线激活预检：{ready}\n\n"
        "现在去板子配置页点击“在线激活”。\n"
        f"{MAC_SOURCE_TIP}"
    )


def format_account_status(data: dict) -> str:
    qq = data.get("qq", "")
    products = data.get("products") or []
    lines = [f"授权状态：{qq}"]
    for product in products:
        if product.get("product") != "s3":
            continue
        lines.append(
            f"S3：{product.get('used', 0)}/{product.get('quota_total', 0)}，剩余 {product.get('remaining', 0)}"
        )
        bindings = product.get("bindings") or []
        if bindings:
            for item in bindings[:8]:
                lines.append(f"- {item.get('mac', '')}：{_status_label(item.get('status', ''))}")
        else:
            lines.append("- 暂无已登记 S3 板子")
    lines.append("")
    lines.append(MAC_SOURCE_TIP)
    return "\n".join(lines)


def format_device_check(data: dict) -> str:
    source = data.get("source") or "-"
    product = str(data.get("product") or "s3").upper()
    return (
        f"在线激活预检通过。\n"
        f"设备：{data.get('mac', '')}\n"
        f"产品：{product}\n"
        f"来源：{source}\n\n"
        f"{MAC_SOURCE_TIP}"
    )


def parse_quota_args(text: str) -> tuple[str, int] | None:
    parts = text.split()
    if len(parts) < 2:
        return None
    if parts[0].upper() == "S3" and len(parts) >= 3:
        qq = extract_qq(parts[1])
        quota = _parse_int(parts[2])
    else:
        qq = extract_qq(parts[0])
        quota = _parse_int(parts[1])
    if not qq or quota is None:
        return None
    return qq, quota


def extract_qq(text: str) -> str:
    match = re.search(r"(?<!\d)([1-9]\d{4,11})(?!\d)", text or "")
    return match.group(1) if match else ""


def extract_mac(text: str) -> str:
    match = re.search(r"([0-9a-fA-F][0-9a-fA-F][:\-\s]?){6}", text or "")
    return match.group(0).strip() if match else ""


def _parse_int(text: str) -> int | None:
    try:
        return max(0, int(text))
    except (TypeError, ValueError):
        return None


def _status_label(status: str) -> str:
    return {"active": "启用", "disabled": "禁用", "revoked": "已解绑"}.get(status, status or "未知")


def _safe_load_config() -> Config:
    try:
        return load_config()
    except ValueError:
        return Config()
