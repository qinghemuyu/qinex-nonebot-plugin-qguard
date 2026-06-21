from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QLicense",
    description="QInEX S3/P4 板子自助登记与授权配额管理。",
    usage="/激活 状态",
    type="application",
    homepage="https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
