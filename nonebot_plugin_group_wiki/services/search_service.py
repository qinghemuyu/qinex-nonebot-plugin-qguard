from nonebot_plugin_group_wiki.models import get_session
from nonebot_plugin_group_wiki.repositories.article_repo import WikiArticleRepo
from nonebot_plugin_group_wiki.repositories.index_repo import WikiSearchIndexRepo
from nonebot_plugin_group_wiki.repositories.scope_config_repo import WikiScopeConfigRepo
from nonebot_plugin_group_wiki.services.skill_registry import (
    FAQ_CATEGORY,
    faq_chunk_allowed_for_categories,
    find_skill,
    match_skill_id,
)
from nonebot_plugin_group_wiki.utils.rerank import SearchHit, score_article

_QUERY_EXPANSIONS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("上位机", "pc端", "pc 端", "电脑端", "电脑程序", "pc客户端", "电脑版"), "QInEX 映射软件 PC端 电脑端 配置面板 上位机"),
    (("配置页", "配置面板", "布键页面", "拖键页面", "web ui"), "配置面板 WebView2 保存配置 布键 工作模式"),
    (("一卡一卡", "卡一卡", "卡卡", "一顿一顿", "忽快忽慢"), "卡顿 掉帧 延迟 回报率 异步 CPU 出帧"),
    (("掉帧", "丢帧", "卡帧"), "卡顿 延迟 回报率 CPU 出帧"),
    (("不跟手", "慢半拍", "拖枪不跟手", "触摸点黏", "滑屏不顺"), "卡顿 丝滑 出帧模式 回报率 异步"),
    (("没反应", "不生效", "按键没用", "没有触点", "无触点", "游戏里没用"), "保存配置 输出模式 触摸屏 参考分辨率 管理员权限 工作模式"),
    (("打不开", "启动不了", "闪退", "配置面板打不开", "空白"), "管理员 WebView2 配套文件 完整解压 杀毒拦截"),
    (("最新版", "新版", "最新版本"), "版本 更新"),
    (
        ("同时按", "组合键", "一起按", "两个键", "斜向", "对角", "wasd", "方向键没", "走位", "按住斜", "wa再", "wd再"),
        "移动摇杆 WASD 一个触点 方向合成 对向抵消 走位 自定义按键 独立触点 摇杆机制",
    ),
    (("自定义按键", "普通按键", "一键多点", "侧键", "鼠标键"), "自定义按键 普通按键 触点 按住 点击 一键多点 键冲突"),
    (("视角滑动", "视角区域", "转视角", "鼠标视角", "鼠标移动"), "视角滑动区域 灵敏度 加速度 纯净模式 自动回中 ALT 鼠标模式"),
    (("鼠标轮盘", "环形技能", "技能轮盘", "tab轮盘", "长按进轮盘"), "鼠标轮盘 短按点击 长按轮盘 滑选 基础层"),
    (("开镜灵敏", "ads", "降灵敏", "开镜太快", "开镜甩飞"), "开镜灵敏度 ADS 降灵敏 右键 开镜触点 视角"),
    (("多态", "背包模式", "商店模式", "地图模式", "再按退出"), "多态交互 背包 商店 地图 打开关闭 光标 投屏 vPointer"),
    (("轻触", "长按", "一键两用", "短按", "长按阈值"), "轻触 长按 双功能 阈值 同键冲突 轻触触点 长按触点"),
    (("手势", "滑动键", "切倍镜", "划菜单", "起点终点"), "手势滑动键 起点 终点 滑动 切倍镜 划菜单 滚轮"),
    (("按键层", "扩展层", "载具层", "法术栏", "切层"), "按键层 扩展层 按住 切换 载具 法术栏 禁用走路摇杆 基础层"),
    (("蓄力", "蓄力瞄准", "手雷", "弓箭", "松手投出"), "蓄力瞄准 起始触点 鼠标拖动 松手投掷 视角不动"),
)


class WikiSearchService:
    async def search(self, query: str, *, group_id: int | None = None, limit: int = 5) -> list[SearchHit]:
        if not query.strip():
            return []
        expanded_query = expand_search_query(query)
        async with get_session() as session:
            article_repo = WikiArticleRepo(session)
            index_repo = WikiSearchIndexRepo(session)
            articles = await article_repo.list_published(group_id=group_id)
            allowed_categories = await WikiScopeConfigRepo(session).allowed_categories(group_id)
            hits: list[SearchHit] = []
            query_skill = find_skill(match_skill_id(expanded_query))
            for article in articles:
                chunks = await index_repo.chunks_by_article(article.id)
                if allowed_categories:
                    allowed = set(allowed_categories)
                    if article.category == FAQ_CATEGORY:
                        if query_skill is not None and not allowed.intersection(query_skill.primary_categories):
                            continue
                        chunks = [chunk for chunk in chunks if faq_chunk_allowed_for_categories(chunk, allowed_categories)]
                        if not chunks:
                            continue
                    elif article.category not in allowed:
                        continue
                hit = score_article(expanded_query, article, chunks)
                if hit is not None:
                    hits.append(hit)
            hits.sort(key=lambda item: item.score, reverse=True)
            for hit in hits[:limit]:
                await article_repo.increment_hit(hit.article)
            await session.commit()
            return hits[:limit]


def expand_search_query(query: str) -> str:
    normalized = query.strip().lower()
    additions: list[str] = []
    for triggers, expansion in _QUERY_EXPANSIONS:
        if any(trigger.lower() in normalized for trigger in triggers):
            additions.append(expansion)
    if not additions:
        return query
    return f"{query}\n{' '.join(additions)}"
