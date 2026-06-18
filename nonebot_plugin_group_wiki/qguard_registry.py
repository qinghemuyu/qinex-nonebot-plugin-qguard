from __future__ import annotations

from nonebot_plugin_group_wiki.services.scope_service import WikiScopeService
from nonebot_plugin_group_wiki.services.skill_registry import WIKI_SKILLS
from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.registry import CommandDescriptor, PluginDescriptor, RegistryContext, register_plugin


def _cmd(
    usage: str,
    summary: str,
    role: QGuardRole,
    *,
    reply_category: str = "command_reply",
) -> CommandDescriptor:
    return CommandDescriptor(
        command=usage.split(maxsplit=1)[0],
        summary=summary,
        usage=usage,
        category="knowledge",
        required_role=role,
        reply_category=reply_category,  # type: ignore[arg-type]
    )


async def _status_provider(context: RegistryContext) -> str:
    if context.group_id is None:
        return "已加载"
    allowed, all_categories = await WikiScopeService().get_group_scope(context.group_id)
    scope = "全部分类" if not allowed else f"{len(allowed)} 个分类"
    return f"范围 {scope}，可用分类 {len(all_categories)} 个，skills {len(WIKI_SKILLS)} 个"


def get_qguard_descriptor() -> PluginDescriptor:
    return PluginDescriptor(
        plugin_id="group_wiki",
        display_name="QInEX 知识库",
        module_name="nonebot_plugin_group_wiki",
        description="导入、检索和按群范围管理 QInEX 软件知识库。",
        commands=(
            _cmd("/问 问题", "按本群知识范围直接问知识库", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/FAQ 关键词", "查询常见问答", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/知识 搜索 关键词", "搜索知识库", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/知识 查看 K0001", "查看知识条目", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/知识 有用 K0001", "反馈知识有用", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/知识 没用 K0001", "反馈知识没用", QGuardRole.MEMBER, reply_category="chat_reply"),
            _cmd("/知识 分类", "查看知识分类", QGuardRole.MEMBER),
            _cmd("/知识 技能", "查看可用 skills", QGuardRole.MEMBER),
            _cmd("/知识 范围", "查看本群知识回答范围", QGuardRole.MEMBER),
            _cmd("/知识 范围 全部", "设置本群知识范围为全部分类", QGuardRole.GROUP_ADMIN),
            _cmd("/知识 范围 分类 分类1,分类2", "按分类设置本群知识范围", QGuardRole.GROUP_ADMIN),
            _cmd("/知识 范围 技能 qinex_recoil_click,qinex_screenhub", "按 skills 设置本群知识范围", QGuardRole.GROUP_ADMIN),
            _cmd("/知识 导入本地", "从本地 Markdown 导入知识库", QGuardRole.GROUP_ADMIN),
            _cmd("/知识 添加 标题 内容", "手动补充知识", QGuardRole.GROUP_ADMIN),
        ),
        default_enabled=True,
        status_provider=_status_provider,
    )


def register_with_qguard() -> None:
    register_plugin(get_qguard_descriptor())
