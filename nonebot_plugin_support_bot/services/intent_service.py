from types import ModuleType
import importlib

from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.services.harassment_service import classify_harassment
from nonebot_plugin_support_bot.services.schemas import SupportIntent


LOW_QUALITY = {"打不开", "用不了", "没反应", "报错了", "不会用", "还是不行", "不行"}
GENERIC_PROBLEM_TERMS = (
    "没反应",
    "用不了",
    "不行",
    "不生效",
    "没效果",
    "失效",
    "点不动",
    "点不了",
    "卡",
    "卡顿",
    "打不开",
)
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
        harassment_severity, _reason = classify_harassment(text, "out_of_scope")
        if harassment_severity >= 2:
            return SupportIntent(
                is_support_request=False,
                intent="out_of_scope",
                confidence=0.95,
                skill="unknown",
                issue_type="out_of_scope",
                should_search_wiki=False,
                reply_strategy="reject",
            )
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
        low_signal_problem = any(word in normalized for word in LOW_QUALITY) or any(
            word in normalized for word in GENERIC_PROBLEM_TERMS
        )
        if _looks_like_raw_log_or_traceback(normalized):
            return SupportIntent(
                is_support_request=False,
                intent="out_of_scope",
                confidence=0.9,
                skill="unknown",
                issue_type="out_of_scope",
                should_search_wiki=False,
                reply_strategy="reject",
            )
        if not skill_registry.is_qinex_related(text) and not low_signal_problem:
            if self.config.support_bot_allow_casual_chat:
                return SupportIntent(
                    is_support_request=False,
                    intent="casual_chat",
                    confidence=0.72,
                    skill="casual",
                    issue_type="casual_chat",
                    should_search_wiki=False,
                    reply_strategy="casual_chat",
                )
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
        diagnostic_fields = self._diagnostic_missing_fields(issue_type, normalized)
        if self._should_ask_diagnostic(text.strip(), normalized, issue_type, is_usage_query, diagnostic_fields):
            return SupportIntent(
                intent="diagnostic_followup",
                confidence=0.68,
                skill=skill,
                issue_type=issue_type,
                need_screenshot=issue_type in {"mapping_not_working", "screenhub_usage", "performance_problem"},
                need_version=True,
                need_config=issue_type in {"mapping_not_working", "config_problem"},
                should_search_wiki=False,
                reply_strategy="ask_followup",
                missing_fields=diagnostic_fields,
            )
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
        if any(word in text for word in ("授权码", "注册码", "订单", "退款", "换绑")):
            return "privacy_or_license"
        if _has_screenhub_marker(text) and _has_performance_marker(text):
            return "screenhub_usage"
        if _has_performance_marker(text):
            return "performance_problem"
        if any(word in text for word in ("投屏", "screenhub", "qinescreen", "vpointer")):
            return "screenhub_usage"
        if any(word in text for word in ("压枪", "连点", "映射", "按键", "鼠标", "没反应", "不生效", "按键没用", "没有触点", "无触点")):
            return "mapping_not_working"
        if "p4" in text:
            return "p4_usage"
        if any(word in text for word in ("打不开", "启动", "闪退", "崩溃", "crash", "空白", "webview2")):
            return "launch_failed"
        if any(word in text for word in ("配置", "怎么", "如何", "教程", "不会")):
            return "config_problem"
        return "usage_question"

    @staticmethod
    def _missing_fields(issue_type: str) -> list[str]:
        if issue_type == "mapping_not_working":
            return ["是按键、鼠标还是压枪没反应", "你用的是 S3、免硬件还是 P4"]
        if issue_type in {"launch_failed", "crash"}:
            return ["卡在哪一步或看到什么提示", "你用的是 S3、免硬件还是 P4"]
        if issue_type == "screenhub_usage":
            return ["是电脑投屏还是手机 APP", "是画面卡还是点不准"]
        if issue_type == "p4_usage":
            return ["P4 现在卡在哪个页面", "手机上有没有出现触点"]
        return ["你用的是哪个功能", "现在卡在哪一步"]

    def _diagnostic_missing_fields(self, issue_type: str, text: str) -> list[str]:
        if issue_type == "mapping_not_working":
            fields = []
            if not _has_device_marker(text):
                fields.append("你用的是 S3、免硬件 ADB 还是 P4")
            if not any(word in text for word in ("所有", "全部", "部分", "有些", "按键", "鼠标", "摇杆", "压枪", "连点", "触点")):
                fields.append("是所有输入没反应，还是只有某个组件/部分按键")
            return fields or self._missing_fields(issue_type)
        if issue_type == "performance_problem":
            fields = []
            if not any(word in text for word in ("滑屏", "投屏", "按键", "画面", "拖枪", "鼠标", "压枪")):
                fields.append("卡的是滑屏、投屏画面，还是按键响应")
            if not _has_device_marker(text):
                fields.append("你用的是 S3、免硬件 ADB 还是 P4")
            return fields or self._missing_fields(issue_type)
        if issue_type == "launch_failed":
            fields = []
            if not any(word in text for word in ("空白", "闪退", "打不开", "报错", "webview2", "启动")):
                fields.append("是打不开、空白、闪退，还是有报错提示")
            if not any(word in text for word in ("上位机", "pc", "电脑", "配置面板", "手机app", "qinescreen")):
                fields.append("打不开的是上位机、配置面板还是手机 APP")
            return fields or self._missing_fields(issue_type)
        if issue_type == "screenhub_usage":
            fields = []
            if not any(word in text for word in ("电脑", "手机", "app", "画面", "控制", "点不准", "卡")):
                fields.append("是电脑投屏、手机 APP，还是控制模式")
            if not any(word in text for word in ("卡", "黑屏", "点不准", "连不上", "没画面")):
                fields.append("现象是画面卡、黑屏、点不准，还是连不上")
            return fields or self._missing_fields(issue_type)
        return self._missing_fields(issue_type)

    @staticmethod
    def _should_ask_diagnostic(
        original: str,
        text: str,
        issue_type: str,
        is_usage_query: bool,
        diagnostic_fields: list[str],
    ) -> bool:
        if is_usage_query or not diagnostic_fields:
            return False
        if issue_type not in {"mapping_not_working", "performance_problem", "launch_failed", "screenhub_usage", "p4_usage"}:
            return False
        if any(marker in text for marker in ("wasd", "wa再", "wd再", "按住wa", "按住wd", "斜向", "对角")):
            return False
        if _has_specific_component_and_symptom(text, issue_type):
            return False
        if len(original) <= 14 and any(term in text for term in GENERIC_PROBLEM_TERMS):
            return True
        if len(diagnostic_fields) >= 2 and len(original) <= 18:
            return True
        return False


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


def _has_device_marker(text: str) -> bool:
    return any(word in text for word in ("s3", "p4", "adb", "免硬件", "硬件", "板子", "数据线", "单机版"))


def _has_screenhub_marker(text: str) -> bool:
    return any(word in text for word in ("投屏", "screenhub", "qinescreen", "vpointer", "画面", "控制模式"))


def _has_performance_marker(text: str) -> bool:
    return any(
        word in text
        for word in (
            "卡",
            "卡顿",
            "延迟",
            "掉帧",
            "丢帧",
            "一卡一卡",
            "卡卡",
            "一顿一顿",
            "忽快忽慢",
            "慢",
            "慢半拍",
            "不跟手",
            "触摸点黏",
            "滑屏不顺",
        )
    )


def _has_specific_component_and_symptom(text: str, issue_type: str) -> bool:
    if not _has_performance_marker(text):
        return False
    if issue_type == "screenhub_usage":
        return _has_screenhub_marker(text)
    if issue_type == "performance_problem":
        component_markers = (
            "p4",
            "s3",
            "adb",
            "免硬件",
            "滑屏",
            "投屏",
            "画面",
            "按键",
            "鼠标",
            "触摸",
            "上位机",
            "回报率",
            "8000",
            "8k",
        )
        return any(marker in text for marker in component_markers)
    return False


def _looks_like_raw_log_or_traceback(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "traceback",
            "modulenotfounderror",
            "exception",
            "stack trace",
            "syntaxerror",
            "typeerror",
            "attributeerror",
        )
    )
