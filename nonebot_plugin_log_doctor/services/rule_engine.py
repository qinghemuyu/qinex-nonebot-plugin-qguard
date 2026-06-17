from nonebot_plugin_log_doctor.rules.builtin import BUILTIN_RULES, BuiltinRule
from nonebot_plugin_log_doctor.services.schemas import DiagnosisResult


class RuleEngine:
    def __init__(self, rules: tuple[BuiltinRule, ...] = BUILTIN_RULES) -> None:
        self.rules = tuple(sorted(rules, key=lambda rule: rule.priority))

    def match(self, text: str) -> DiagnosisResult | None:
        lower_text = text.lower()
        for rule in self.rules:
            evidence = [pattern for pattern in rule.patterns if pattern in lower_text]
            if evidence:
                return rule.to_result(evidence)
        return None

    def list_rules(self) -> list[BuiltinRule]:
        return list(self.rules)
