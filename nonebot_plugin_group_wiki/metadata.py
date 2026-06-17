from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="GroupWiki 群知识库",
    description="面向 QInEX 售后的群知识库插件，支持本地知识库导入、搜索、查看和基于知识库的 AI 问答。",
    usage="/知识 搜索 关键词\n/问 问题\n/知识 导入本地",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
