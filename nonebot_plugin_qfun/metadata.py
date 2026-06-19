from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QFun",
    description="QInEX 群娱乐统计插件，提供词云和每日群内推送。",
    usage="/娱乐 帮助",
    type="application",
    homepage="https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
