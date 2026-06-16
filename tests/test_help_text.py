from nonebot_plugin_qguard.commands.root import HELP_TEXT


def test_help_text_mentions_rule_commands() -> None:
    assert "/管 规则 添加 关键词 xxx 警告" in HELP_TEXT
    assert "/管 规则 添加 正则 xxx 踢出" in HELP_TEXT
    assert "/管 规则 删除 ID" in HELP_TEXT
    assert "/管 规则 列表" in HELP_TEXT
    assert "/管 规则 测试 文本" in HELP_TEXT
    assert "/管 广告检测 开" in HELP_TEXT
    assert "/管 刷屏检测 开" in HELP_TEXT
    assert "/管 自动撤回 90s" in HELP_TEXT
    assert "/管 自动撤回 0" in HELP_TEXT
    assert "/管 积分 @用户" in HELP_TEXT
    assert "/管 积分 清零 @用户" in HELP_TEXT
    assert "/管 白名单 添加 @用户 原因" in HELP_TEXT
    assert "/管 黑名单 添加 @用户 原因" in HELP_TEXT
    assert "/管 入群审核 开" in HELP_TEXT
    assert "/管 入群暗号 设置 xxx" in HELP_TEXT
    assert "/管 新人保护 开" in HELP_TEXT
    assert "/管 新人保护 时长 24h" in HELP_TEXT
    assert "/管 群名锁 开 新群名" in HELP_TEXT
    assert "/管 匿名锁 开 开|关" in HELP_TEXT
    assert "/管 巡检 权限" in HELP_TEXT
    assert "/管 自动巡检 开" in HELP_TEXT
    assert "/管 自动巡检 间隔 5s" in HELP_TEXT
