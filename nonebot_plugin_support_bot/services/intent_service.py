from nonebot_plugin_support_bot.config import Config, load_config
from nonebot_plugin_support_bot.services.schemas import SupportIntent


LOG_MARKERS = (
    "traceback",
    "exception",
    "error",
    "module not found",
    "modulenotfounderror",
    "attributeerror",
    "runtimeerror",
    "sqlite",
    "[error]",
    "报错",
    "错误",
)

LOW_QUALITY = {"打不开", "用不了", "没反应", "报错了", "不会用", "还是不行", "不行"}


class IntentService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    async def classify(self, text: str, *, force_log: bool = False, force_ticket: bool = False) -> SupportIntent:
        normalized = text.strip().lower()
        if force_ticket:
            return self._ticket_intent(text, issue_type=self._guess_issue_type(normalized))
        if force_log or self._looks_like_log(normalized):
            return SupportIntent(
                intent="diagnose_log",
                confidence=0.92,
                issue_type=self._guess_issue_type(normalized),
                need_log=False,
                need_version=True,
                should_search_wiki=True,
                should_diagnose_log=True,
                should_create_ticket=False,
                reply_strategy="diagnose_log",
                missing_fields=["软件版本", "系统版本"] if len(text.strip()) < 120 else [],
            )
        issue_type = self._guess_issue_type(normalized)
        if issue_type in {"license_problem", "payment_order", "account_problem"}:
            return self._ticket_intent(text, issue_type=issue_type)
        is_usage_query = any(word in normalized for word in ("怎么", "如何", "教程", "配置", "设置"))
        if (normalized in LOW_QUALITY or len(text.strip()) < 8) and not is_usage_query:
            return SupportIntent(
                intent="collect_info",
                confidence=0.86,
                issue_type=issue_type,
                need_log=issue_type in {"launch_failed", "crash", "bug_report"},
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
            issue_type=issue_type,
            need_log=issue_type in {"launch_failed", "crash", "bug_report"},
            need_screenshot=issue_type in {"mapping_not_working", "compatibility_problem"},
            need_version=True,
            need_config=issue_type in {"mapping_not_working", "config_problem"},
            should_search_wiki=True,
            should_diagnose_log=False,
            should_create_ticket=False,
            reply_strategy="answer",
            missing_fields=[],
        )

    @staticmethod
    def _looks_like_log(text: str) -> bool:
        return any(marker in text for marker in LOG_MARKERS)

    @staticmethod
    def _ticket_intent(text: str, *, issue_type: str) -> SupportIntent:
        return SupportIntent(
            intent="human_handoff",
            confidence=0.9,
            issue_type=issue_type,
            urgency="high" if any(word in text for word in ("付费", "订单", "授权", "激活")) else "normal",
            need_version=issue_type not in {"payment_order", "license_problem"},
            should_search_wiki=False,
            should_diagnose_log=False,
            should_create_ticket=True,
            reply_strategy="human_handoff",
            missing_fields=["软件版本", "问题现象"] if len(text.strip()) < 12 else [],
        )

    @staticmethod
    def _guess_issue_type(text: str) -> str:
        if any(word in text for word in ("授权", "激活", "授权码", "注册码")):
            return "license_problem"
        if any(word in text for word in ("付款", "支付", "订单", "退款")):
            return "payment_order"
        if any(word in text for word in ("压枪", "连点", "映射", "按键", "鼠标", "没反应")):
            return "mapping_not_working"
        if any(word in text for word in ("配置", "怎么", "如何", "教程", "不会")):
            return "config_problem"
        if any(word in text for word in ("卡顿", "延迟", "掉帧", "慢")):
            return "performance_problem"
        if any(word in text for word in ("打不开", "启动", "闪退", "崩溃", "crash")):
            return "launch_failed"
        if any(word in text for word in ("bug", "异常", "报错", "错误", "traceback")):
            return "bug_report"
        return "usage_question"

    @staticmethod
    def _missing_fields(issue_type: str) -> list[str]:
        if issue_type == "mapping_not_working":
            return ["软件版本", "游戏名称", "分辨率", "是否管理员权限运行", "当前配置文件", "具体现象"]
        if issue_type in {"launch_failed", "crash", "bug_report"}:
            return ["软件版本", "系统版本", "完整报错或日志", "复现步骤"]
        if issue_type in {"license_problem", "payment_order"}:
            return ["订单号后 4 位或授权码后 4 位", "绑定 QQ", "错误提示截图"]
        return ["软件版本", "系统版本", "具体现象", "截图或日志"]
