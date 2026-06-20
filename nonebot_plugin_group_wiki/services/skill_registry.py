from __future__ import annotations

from dataclasses import dataclass

FAQ_CATEGORY = "FAQ问答对"
TERMS_CATEGORY = "12_术语别名与口语化问法"
COMPONENT_CATEGORY = "13_映射组件诊断卡片"
SUPPORT_CATEGORY = "14_智能客服与售后闭环"


@dataclass(frozen=True, slots=True)
class WikiSkill:
    skill_id: str
    name: str
    categories: tuple[str, ...]
    keywords: tuple[str, ...]
    answer_policy: tuple[str, ...] = ()

    @property
    def primary_categories(self) -> tuple[str, ...]:
        return tuple(category for category in self.categories if category != FAQ_CATEGORY)


WIKI_SKILLS: tuple[WikiSkill, ...] = (
    WikiSkill(
        skill_id="qinex_basic",
        name="基础使用与选型",
        categories=(
            "01_产品简介与选型",
            "02_硬件模式(ESP32-S3)接线与上手",
            "03_免硬件模式(数据线ADB)",
            "11_激活与安全说明",
            TERMS_CATEGORY,
            FAQ_CATEGORY,
        ),
        keywords=(
            "qinex",
            "是什么",
            "选哪个",
            "硬件模式",
            "免硬件",
            "adb",
            "s3",
            "连接",
            "上手",
            "激活",
            "授权",
            "上位机",
            "pc端",
            "电脑端",
            "电脑程序",
            "映射软件",
        ),
    ),
    WikiSkill(
        skill_id="qinex_activation",
        name="激活与安全说明",
        categories=("11_激活与安全说明", FAQ_CATEGORY),
        keywords=("激活", "授权", "授权码", "注册码", "s3", "p4", "板子", "硬件", "板子激活", "s3激活", "p4激活", "激活入口", "怎么填", "哪里填"),
    ),
    WikiSkill(
        skill_id="qinex_mapping",
        name="映射与配置面板",
        categories=(
            "04_配置面板-基础布键",
            "05_高级映射(开镜背包载具手势蓄力)",
            COMPONENT_CATEGORY,
            TERMS_CATEGORY,
            FAQ_CATEGORY,
        ),
        keywords=(
            "布键",
            "映射",
            "按键",
            "鼠标",
            "摇杆",
            "走位",
            "wasd",
            "方向键",
            "同时按",
            "组合键",
            "斜向",
            "对角",
            "抵消",
            "自定义按键",
            "触点",
            "视角",
            "视角滑动",
            "鼠标轮盘",
            "配置文件",
            "开镜",
            "开镜灵敏度",
            "ads",
            "背包",
            "多态交互",
            "轻触",
            "长按",
            "载具",
            "手势",
            "手势滑动",
            "按键层",
            "蓄力",
            "蓄力瞄准",
            "上位机",
            "pc端",
            "电脑端",
            "配置面板",
            "布键页面",
            "web ui",
            "校准",
            "触摸校准",
            "参考分辨率",
            "黑边",
            "坐标",
            "坐标偏移",
            "点位偏",
            "点不准",
            "部分按键",
            "按键失效",
        ),
    ),
    WikiSkill(
        skill_id="qinex_recoil_click",
        name="连点与压枪",
        categories=("06_连点与压枪", FAQ_CATEGORY),
        keywords=("连点", "turbo", "压枪", "后坐力", "recoil", "开火键", "下拉强度", "抖动"),
        answer_policy=("回答压枪时必须提醒反作弊/封号风险，开启自行承担风险。",),
    ),
    WikiSkill(
        skill_id="qinex_screenhub",
        name="投屏与手机 APP",
        categories=("07_投屏ScreenHub", "09_QInEScreen手机APP", TERMS_CATEGORY, FAQ_CATEGORY),
        keywords=(
            "投屏",
            "screenhub",
            "控制模式",
            "画面",
            "卡顿",
            "码率",
            "qinescreen",
            "vpointer",
            "手机app",
            "手机 app",
            "手机端",
            "点对点",
        ),
    ),
    WikiSkill(
        skill_id="qinex_p4",
        name="P4 双模式",
        categories=("08_P4单机版", "09_QInEScreen手机APP", TERMS_CATEGORY, FAQ_CATEGORY),
        keywords=(
            "p4",
            "p4单机",
            "p4 单机",
            "p4上位机",
            "p4 上位机",
            "单机版",
            "单机模式",
            "上位机模式",
            "modea",
            "mode a",
            "modeb",
            "mode b",
            "不要电脑",
            "不开电脑",
            "板载配置页",
            "kmboxnet",
            "触摸校准",
            "手机配p4",
            "激活页",
            "下位机",
            "触摸桥",
            "串口",
            "com",
            "8000hz",
            "8k",
            "usb hs",
            "ota切换",
            "eco2",
            "eco6",
        ),
    ),
    WikiSkill(
        skill_id="qinex_troubleshooting",
        name="排障与卡顿",
        categories=("10_排障与卡顿速查", TERMS_CATEGORY, FAQ_CATEGORY),
        keywords=(
            "卡顿",
            "延迟",
            "掉帧",
            "丢帧",
            "一卡一卡",
            "卡卡",
            "一顿一顿",
            "忽快忽慢",
            "慢半拍",
            "拖枪不跟手",
            "触摸点黏",
            "滑屏不顺",
            "连不上",
            "没反应",
            "不生效",
            "按键没用",
            "没有触点",
            "无触点",
            "打不开",
            "启动不了",
            "闪退",
            "配置面板打不开",
            "空白",
            "webview2",
            "管理员权限",
            "回报率",
            "异步",
            "触摸点",
            "校准",
            "触摸校准",
            "参考分辨率",
            "黑边",
            "坐标偏移",
            "点位偏",
            "点不准",
            "部分按键失效",
            "部分映射按键失效",
            "反作弊",
            "上位机",
            "pc端",
            "电脑端",
            "最新版",
            "新版",
        ),
    ),
    WikiSkill(
        skill_id="qinex_terms",
        name="术语别名与口语化问法",
        categories=(TERMS_CATEGORY, FAQ_CATEGORY),
        keywords=(
            "术语",
            "别名",
            "叫法",
            "说法",
            "是什么意思",
            "什么意思",
            "是什么东西",
            "上位机",
            "pc端",
            "pc 端",
            "电脑端",
            "电脑版",
            "电脑程序",
            "映射软件",
            "配置面板",
            "手机端",
            "手机app",
            "qinescreen",
            "vpointer",
        ),
    ),
    WikiSkill(
        skill_id="qinex_ai_support",
        name="智能客服与售后闭环",
        categories=(SUPPORT_CATEGORY, TERMS_CATEGORY, FAQ_CATEGORY),
        keywords=(
            "智能问答",
            "智能客服",
            "客服",
            "售后",
            "求助",
            "机器人",
            "问诊",
            "低置信度",
            "追问",
            "连续对话",
            "未命中",
            "知识缺口",
            "缺口",
            "补知识",
            "解决了",
            "还是不行",
            "主人",
            "/客服",
            "/求助",
            "/售后",
            "/不会用",
            "/知识 范围",
            "/知识 技能",
        ),
    ),
)

SKILL_BY_ID = {skill.skill_id: skill for skill in WIKI_SKILLS}


def list_wiki_skills() -> tuple[WikiSkill, ...]:
    return WIKI_SKILLS


def find_skill(skill_id: str) -> WikiSkill | None:
    return SKILL_BY_ID.get(skill_id.strip())


def categories_for_skill_ids(skill_ids: list[str], *, include_faq: bool = False) -> tuple[list[str], list[str]]:
    categories: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for raw in skill_ids:
        skill = find_skill(raw)
        if skill is None:
            rejected.append(raw)
            continue
        source = skill.categories if include_faq else skill.primary_categories
        for category in source:
            if category not in seen:
                seen.add(category)
                categories.append(category)
    return categories, rejected


def match_skill_id(text: str) -> str:
    normalized = text.strip().lower()
    best_skill = "unknown"
    best_score = 0
    for skill in WIKI_SKILLS:
        score = sum(1 for keyword in skill.keywords if keyword.lower() in normalized)
        if score > best_score:
            best_score = score
            best_skill = skill.skill_id
    return best_skill


def is_qinex_related(text: str) -> bool:
    normalized = text.strip().lower()
    strong_product_markers = (
        "qinex",
        "映射",
        "映射软件",
        "上位机",
        "pc端",
        "电脑端",
        "电脑程序",
        "压枪",
        "连点",
        "投屏",
        "screenhub",
        "qinescreen",
        "p4",
        "p4上位机",
        "p4单机",
        "modeb",
        "modea",
        "s3",
        "adb",
        "键鼠",
        "配置面板",
        "布键",
        "触点",
        "输出模式",
        "参考分辨率",
        "自定义按键",
        "视角滑动",
        "鼠标轮盘",
        "开镜灵敏度",
        "多态交互",
        "轻触",
        "长按",
        "手势滑动",
        "按键层",
        "蓄力瞄准",
    )
    if any(marker in normalized for marker in strong_product_markers):
        return True
    if _looks_like_mapping_component_question(normalized):
        return True
    skill_id = match_skill_id(text)
    return skill_id not in {"unknown", "qinex_mapping"}


def _looks_like_mapping_component_question(normalized: str) -> bool:
    weak_mapping_markers = (
        "摇杆",
        "走位",
        "wasd",
        "方向键",
        "鼠标",
        "按键",
        "按键失效",
        "部分按键",
        "部分映射",
        "右键",
        "左键",
        "开镜",
        "视角",
        "轮盘",
        "背包",
        "商店",
        "地图",
        "载具",
        "手势",
        "蓄力",
        "多态",
        "按键层",
        "轻触",
        "长按",
        "ads",
        "wa再",
        "wd再",
    )
    component_context_markers = (
        "按住",
        "同时按",
        "一起按",
        "组合",
        "斜向",
        "对角",
        "抵消",
        "没反应",
        "不触发",
        "不生效",
        "没用",
        "游戏里",
        "触点",
        "映射",
        "摆好",
        "配置",
        "设置",
        "绑定",
        "怎么配",
        "怎么调",
        "灵敏度",
        "太飘",
        "甩飞",
        "点不准",
        "校准",
        "坐标偏移",
        "触摸校准",
        "切层",
        "触发",
        "开了",
        "没效果",
        "移动摇杆",
        "自定义",
        "一个方向",
    )
    return any(marker in normalized for marker in weak_mapping_markers) and any(
        marker in normalized for marker in component_context_markers
    )


def faq_chunk_allowed_for_categories(chunk: str, allowed_categories: list[str]) -> bool:
    if not allowed_categories:
        return True
    allowed = set(allowed_categories)
    if FAQ_CATEGORY in allowed and len(allowed) == 1:
        return True
    normalized = chunk.strip().lower()
    for skill in WIKI_SKILLS:
        if not allowed.intersection(skill.primary_categories):
            continue
        if any(keyword.lower() in normalized for keyword in skill.keywords):
            return True
    return False


def describe_wiki_skills() -> str:
    lines = ["QInEX 知识 Skills："]
    for skill in WIKI_SKILLS:
        lines.append(f"- {skill.skill_id}：{skill.name}")
        lines.append("  分类：" + "、".join(skill.primary_categories))
    return "\n".join(lines)
