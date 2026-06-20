from pathlib import Path

from nonebot_plugin_qguard.commands.root import HELP_TEXT


def test_help_text_lists_readme_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_commands = [line.strip() for line in readme.splitlines() if line.startswith("/管 ")]
    help_lines = set(HELP_TEXT.splitlines())

    missing = [command for command in readme_commands if command not in help_lines]

    assert missing == []


def test_help_text_mentions_rule_commands() -> None:
    assert "/管 规则 添加 关键词 xxx 警告" in HELP_TEXT
    assert "/管 规则 添加 正则 xxx 踢出" in HELP_TEXT
    assert "/管 规则 删除 ID" in HELP_TEXT
    assert "/管 规则 列表" in HELP_TEXT
    assert "/管 规则 测试 文本" in HELP_TEXT
    assert "/管 广告检测 开" in HELP_TEXT
    assert "/管 广告词 添加 xxx" in HELP_TEXT
    assert "/管 广告词 列表" in HELP_TEXT
    assert "/管 刷屏检测 开" in HELP_TEXT
    assert "/管 自动撤回 90s" in HELP_TEXT
    assert "/管 自动撤回 0" in HELP_TEXT
    assert "/管 自动撤回 分类 指令|聊天|全部|关闭" in HELP_TEXT
    assert "/管 自动清理 状态" in HELP_TEXT
    assert "/管 自动清理 提醒 30d 60d" in HELP_TEXT
    assert "/管 自动清理 踢出 90d" in HELP_TEXT
    assert "/管 撤回 数量" in HELP_TEXT
    assert "/管 积分 @用户" in HELP_TEXT
    assert "/管 积分 清零 @用户" in HELP_TEXT
    assert "/管 白名单 添加 @用户 原因" in HELP_TEXT
    assert "/管 黑名单 添加 @用户 原因" in HELP_TEXT
    assert "/管 黑名单 全局添加 @用户 原因" in HELP_TEXT
    assert "/管 黑名单 全局列表" in HELP_TEXT
    assert "/管 角色 @用户 普通|可信|小管理" in HELP_TEXT
    assert "/管 角色查 @用户" in HELP_TEXT
    assert "/管 入群审核 开" in HELP_TEXT
    assert "/管 入群暗号 设置 xxx" in HELP_TEXT
    assert "/管 入群欢迎 开" in HELP_TEXT
    assert "/管 入群欢迎 模板 文本" in HELP_TEXT
    assert "/管 日志 @用户" in HELP_TEXT
    assert "/管 名片日志 @用户" in HELP_TEXT
    assert "/管 处罚日志 @用户" in HELP_TEXT
    assert "/管 最近消息 @用户" in HELP_TEXT
    assert "/管 消息 消息ID" in HELP_TEXT
    assert "/管 新人保护 开" in HELP_TEXT
    assert "/管 新人保护 时长 24h" in HELP_TEXT
    assert "/管 新人禁链接 开|关" in HELP_TEXT
    assert "/管 新人禁图片 开|关" in HELP_TEXT
    assert "/管 群名锁 开 新群名" in HELP_TEXT
    assert "/管 匿名锁 开 开|关" in HELP_TEXT
    assert "/管 全体禁言 开|关" in HELP_TEXT
    assert "/管 巡检 权限" in HELP_TEXT
    assert "/管 自动巡检 开" in HELP_TEXT
    assert "/管 自动巡检 间隔 5s" in HELP_TEXT
