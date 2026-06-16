from nonebot_plugin_qguard.commands.root import HELP_TEXT


def test_help_text_mentions_rule_commands() -> None:
    assert "/管 规则 添加 关键词 xxx 警告" in HELP_TEXT
    assert "/管 规则 添加 正则 xxx 踢出" in HELP_TEXT
    assert "/管 规则 删除 ID" in HELP_TEXT
    assert "/管 规则 列表" in HELP_TEXT
    assert "/管 规则 测试 文本" in HELP_TEXT
