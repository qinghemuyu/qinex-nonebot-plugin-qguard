from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="LogDoctor 日志诊断",
    description="面向 NoneBot / OneBot / Python / Linux 常见报错的日志诊断插件，支持规则诊断和 AI Core 兜底。",
    usage="/诊断 <日志文本>\n/诊断 最近\n/诊断 规则列表",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
