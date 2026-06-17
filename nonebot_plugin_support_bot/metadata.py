from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="SupportBot 售后客服",
    description="面向 QInEX 的 AI 售后入口，支持求助、报错诊断、知识库问答和轻量工单。",
    usage="/求助 问题\n/报错 日志\n/人工\n/工单 创建 问题",
    type="application",
    homepage="https://github.com/qinghemuyu/qinex-nonebot-plugin-qguard",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
