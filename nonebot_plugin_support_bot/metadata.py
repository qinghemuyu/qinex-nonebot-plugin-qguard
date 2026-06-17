from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QInEX 智能问答",
    description="QInEX 映射软件专属知识库智能问答入口，按群级知识范围和 skills 回答。",
    usage="/求助 问题\n/售后 问题\n/不会用 功能名称\n/知识 范围",
    type="application",
    homepage="https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
