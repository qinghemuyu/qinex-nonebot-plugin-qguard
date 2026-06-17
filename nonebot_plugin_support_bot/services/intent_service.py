from types import ModuleType
import importlib

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.services.schemas import SupportIntent


LOW_QUALITY = {"打不开", "用不了", "没反应", "报错了", "不会用", "还是不行", "不行"}
LICENSE_TERMS = ("授权", "激活", "授权码", "注册码", "订单", "退款", "换绑", "破解", "绕过", "密钥")
BLOCKED_LICENSE_TERMS = ("订单", "退款", "换绑", "破解", "绕过", "密钥", "生成", "算法", "找回", "查询")
SAFE_ACTIVATION_MARKERS = (
    "s3",
    "p4",
    "板子",
    "硬件",
    "设备",
    "单机",
    "esp32",
    "激活入口",
    "怎么激活",
    "如何激活",
    "怎么填",
    "哪里填",
)


class IntentService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    async def classify(self, text: str) -> SupportIntent:
        normalized = text.strip().lower()
        skill_registry = _get_skill_registry()
        skill = skill_registry.match_skill_id(text)
        if _is_license_or_privacy_question(normalized) and not _is_safe_activation_question(normalized):
            return SupportIntent(
                intent="privacy_or_license",
                confidence=0.88,
                skill="unknown",
                issue_type="privacy_or_license",
                need_screenshot=False,
                need_version=False,
                should_search_wiki=False,
                reply_strategy="safe_no_answer",
            )
        if not skill_registry.is_qinex_related(text) and not any(word in normalized for word in LOW_QUALITY):
            return SupportIntent(
                is_support_request=False,
                intent="out_of_scope",
                confidence=0.9,
                skill="unknown",
                issue_type="out_of_scope",
                should_search_wiki=False,
                reply_strategy="reject",
            )
        issue_type = self._guess_issue_type(normalized)
        is_usage_query = any(word in normalized for word in ("怎么", "如何", "教程", "配置", "设置"))
        if (normalized in LOW_QUALITY or len(text.strip()) < 8) and not is_usage_query:
            return SupportIntent(
                intent="collect_info",
                confidence=0.86,
                skill=skill,
                issue_type=issue_type,
                need_screenshot=True,
                need_version=True,
                need_config=issue_type in {"mapping_not_working", "config_problem"},
                should_search_wiki=False,
                reply_strategy="ask_followup",
                missing_fields=self._missing_fields(issue_type),
            )
        return SupportIntent(
            intent="support_question",
            confidence=0.82,
            skill=skill,
            issue_type=issue_type,
            need_screenshot=issue_type in {"mapping_not_working", "compatibility_problem"},
            need_version=True,
            need_config=issue_type in {"mapping_not_working", "config_problem"},
            should_search_wiki=True,
            reply_strategy="answer",
            missing_fields=[],
        )

    @staticmethod
    def _guess_issue_type(text: str) -> str:
        if _is_safe_activation_question(text):
            return "activation_usage"
        if "p4" in text:
            return "p4_usage"
        if any(word in text for word in ("投屏", "screenhub", "qinescreen", "vpointer")):
            return "screenhub_usage"
        if any(word in text for word in ("授权码", "注册码", "订单", "退款", "换绑")):
            return "privacy_or_license"
        if any(word in text for word in ("压枪", "连点", "映射", "按键", "鼠标", "没反应")):
            return "mapping_not_working"
        if any(word in text for word in ("配置", "怎么", "如何", "教程", "不会")):
            return "config_problem"
        if any(word in text for word in ("卡顿", "延迟", "掉帧", "慢")):
            return "performance_problem"
        if any(word in text for word in ("打不开", "启动", "闪退", "崩溃", "crash")):
            return "launch_failed"
        return "usage_question"

    @staticmethod
    def _missing_fields(issue_type: str) -> list[str]:
        if issue_type == "mapping_not_working":
            return ["是按键、鼠标还是压枪没反应", "使用的是 S3、免硬件还是 P4", "是否管理员权限运行"]
        if issue_type in {"launch_failed", "crash"}:
            return ["QInEX 版本", "使用模式：S3 / 免硬件 / P4", "卡在哪一步或看到什么提示"]
        if issue_type == "screenhub_usage":
            return ["是 PC 投屏还是手机 APP", "画面问题还是控制问题", "当前连接方式"]
        if issue_type == "p4_usage":
            return ["P4 卡在哪个页面", "手机是否出现触点", "是否用手机 APP 配置 P4"]
        return ["使用的是哪个功能", "卡在哪一步", "当前看到的现象"]


def _get_skill_registry() -> ModuleType:
    try:
        return importlib.import_module("nonebot_plugin_group_wiki.services.skill_registry")
    except ModuleNotFoundError as exc:
        if exc.name and not exc.name.startswith("nonebot_plugin_group_wiki"):
            raise
    package_parts = (__package__ or "").split(".")
    if "nonebot_plugin_support_bot" in package_parts:
        index = package_parts.index("nonebot_plugin_support_bot")
        sibling_module = ".".join(
            [*package_parts[:index], "nonebot_plugin_group_wiki", "services", "skill_registry"]
        )
        return importlib.import_module(sibling_module)
    raise ModuleNotFoundError("nonebot_plugin_group_wiki")


def _is_license_or_privacy_question(text: str) -> bool:
    return any(word in text for word in LICENSE_TERMS)


def _is_safe_activation_question(text: str) -> bool:
    if any(word in text for word in BLOCKED_LICENSE_TERMS):
        return False
    if "激活" not in text and "授权" not in text and "授权码" not in text and "注册码" not in text:
        return False
    return any(marker in text for marker in SAFE_ACTIVATION_MARKERS)
