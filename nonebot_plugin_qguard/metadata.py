from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="QGuard 群管",
    description="基于 NoneBot 2 + OneBot v11 的 QQ 群安全管理插件，支持禁言、踢人、撤回、群名片锁和日志审计。",
    usage="""
/管 帮助
/管 状态
/管 禁 @用户 10m 原因
/管 名片 @用户 新名片
/管 名片锁 @用户 固定名片
/管 名片扫描
""",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
