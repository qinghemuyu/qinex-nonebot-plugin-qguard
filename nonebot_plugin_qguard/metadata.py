from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="QGuard 群管",
    description="基于 NoneBot 2 + OneBot v11 的 QQ 群安全管理插件，支持群管、名片锁、自动审核、入群审核和日志审计。",
    usage="""
/管 帮助
/管 状态
/管 禁 @用户 10m 原因
/管 名片 @用户 新名片
/管 名片锁 @用户 固定名片
/管 名片扫描
/管 规则 添加 关键词 xxx 禁言10m
/管 广告检测 开
""",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
