from nonebot.plugin import PluginMetadata

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="AI Core",
    description="统一的 OpenAI-compatible AI 调用核心，提供限流、缓存、脱敏、结构化 JSON 输出和调用日志。",
    usage="/ai状态",
    type="library",
    config=Config,
    supported_adapters={"~onebot.v11"},
)
