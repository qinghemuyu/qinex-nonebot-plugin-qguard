from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="GroupWiki 群知识库",
    description="QInEX 映射软件知识库插件，支持真实分类、skills、群级回答范围和基于知识库的 AI 问答。",
    usage="/知识 搜索 关键词\n/问 问题\n/知识 技能\n/知识 范围",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
