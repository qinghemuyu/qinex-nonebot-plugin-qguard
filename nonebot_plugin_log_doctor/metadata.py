from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="LogDoctor 内部诊断服务",
    description="内部保留的日志诊断服务；当前 QInEX 智能问答方案不注册群内诊断命令。",
    usage="当前不提供群命令。",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
