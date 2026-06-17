from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="SupportBot 知识问答",
    description="面向 QInEX 的知识库智能问答入口，按群级知识范围回答。",
    usage="/求助 问题\n/售后 问题\n/不会用 功能名称\n/知识 范围",
    type="application",
    homepage="https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
