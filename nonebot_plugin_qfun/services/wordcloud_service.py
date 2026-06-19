from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from nonebot_plugin_qfun.config import Config, load_config
from nonebot_plugin_qfun.models import get_session
from nonebot_plugin_qfun.repositories.group_config_repo import QFunGroupConfigRepo


DOMAIN_TERMS = (
    "QInEX",
    "QInEScreen",
    "ScreenHub",
    "上位机",
    "免硬件",
    "数据线",
    "ADB",
    "ESP32",
    "S3",
    "P4",
    "映射",
    "压枪",
    "连点",
    "投屏",
    "校准",
    "摇杆",
    "移动摇杆",
    "视角摇杆",
    "宏",
    "触摸",
    "激活",
    "配置",
    "保存配置",
    "网页配置",
    "鼠标",
    "键盘",
    "手柄",
    "固件",
    "遮罩",
    "卡顿",
    "断触",
    "蓝牙",
    "回报率",
)
STOPWORDS = {
    "这个",
    "那个",
    "什么",
    "怎么",
    "为什么",
    "是不是",
    "可以",
    "不能",
    "没有",
    "还是",
    "然后",
    "就是",
    "一下",
    "一个",
    "已经",
    "现在",
    "感觉",
    "时候",
    "问题",
    "功能",
    "使用",
    "需要",
    "的话",
    "是不是",
    "怎么办",
}
COMMAND_PREFIXES = ("/", "／", "!")


@dataclass(frozen=True)
class WordCloudTerm:
    word: str
    count: int


@dataclass(frozen=True)
class WordCloudPeriod:
    label: str
    normalized: str
    since: datetime
    until: datetime


@dataclass(frozen=True)
class WordCloudResult:
    group_id: int
    period: WordCloudPeriod
    message_count: int
    user_count: int
    terms: list[WordCloudTerm]


class QFunService:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or _safe_load_config()

    async def status(self, group_id: int | None = None) -> str:
        if group_id is None:
            return "QFun 已加载，支持词云和每日定时推送。"
        async with get_session() as session:
            item = await QFunGroupConfigRepo(session, self.config).get_or_create(group_id)
            await session.commit()
        schedule = "开" if item.wordcloud_schedule_enabled else "关"
        enabled = "开" if item.enabled else "关"
        return (
            "QFun 状态\n"
            f"插件启用：{enabled}\n"
            f"每日词云：{schedule}\n"
            f"发送时间：{item.wordcloud_schedule_time}\n"
            f"统计范围：{item.wordcloud_schedule_period}"
        )

    async def is_group_enabled(self, group_id: int) -> bool:
        async with get_session() as session:
            item = await QFunGroupConfigRepo(session, self.config).get_or_create(group_id)
            await session.commit()
            return bool(item.enabled)

    async def set_enabled(self, group_id: int, enabled: bool, operator_id: int | None = None) -> str:
        async with get_session() as session:
            await QFunGroupConfigRepo(session, self.config).set_enabled(group_id, enabled, operator_id)
            await session.commit()
        return f"QFun 已{'开启' if enabled else '关闭'}。"

    async def set_wordcloud_schedule(
        self,
        group_id: int,
        *,
        enabled: bool,
        schedule_time: str | None = None,
        period_text: str | None = None,
        operator_id: int | None = None,
    ) -> str:
        parsed_time = parse_schedule_time(schedule_time) if schedule_time is not None else None
        period = resolve_period(period_text or self.config.qfun_wordcloud_default_period)
        async with get_session() as session:
            item = await QFunGroupConfigRepo(session, self.config).set_wordcloud_schedule(
                group_id,
                enabled=enabled,
                schedule_time=parsed_time,
                period=period.normalized,
                operator_id=operator_id,
            )
            await session.commit()
        if not enabled:
            return "每日词云已关闭。"
        return f"每日词云已开启：每天 {item.wordcloud_schedule_time} 发送，范围 {item.wordcloud_schedule_period}。"

    async def build_wordcloud(
        self,
        group_id: int,
        period_text: str = "今日",
        *,
        now: datetime | None = None,
    ) -> WordCloudResult:
        period = resolve_period(period_text, now=now)
        messages = await self._list_messages(group_id, since=period.since, until=period.until)
        counter: Counter[str] = Counter()
        user_ids: set[int] = set()
        message_count = 0
        for message in messages:
            text = (getattr(message, "plain_text", None) or "").strip()
            if not text or text.startswith(COMMAND_PREFIXES):
                continue
            tokens = tokenize_text(text)
            if not tokens:
                continue
            counter.update(tokens)
            user_ids.add(int(getattr(message, "user_id", 0) or 0))
            message_count += 1

        terms = [
            WordCloudTerm(word=word, count=count)
            for word, count in sorted(counter.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[
                : max(1, self.config.qfun_wordcloud_top_limit)
            ]
        ]
        return WordCloudResult(
            group_id=group_id,
            period=period,
            message_count=message_count,
            user_count=len(user_ids),
            terms=terms,
        )

    async def render_wordcloud(self, group_id: int, period_text: str = "今日") -> str:
        return format_wordcloud(await self.build_wordcloud(group_id, period_text))

    async def due_wordcloud_messages(self, now: datetime | None = None) -> list[tuple[int, str]]:
        now = now or datetime.now()
        messages: list[tuple[int, str]] = []
        async with get_session() as session:
            repo = QFunGroupConfigRepo(session, self.config)
            due_groups = await repo.list_due_wordcloud_groups(now)
            for item in due_groups:
                text = await self.render_wordcloud(item.group_id, item.wordcloud_schedule_period)
                messages.append((item.group_id, text))
            await session.commit()
        return messages

    async def mark_wordcloud_sent(self, group_id: int, now: datetime | None = None) -> None:
        now = now or datetime.now()
        async with get_session() as session:
            await QFunGroupConfigRepo(session, self.config).mark_wordcloud_sent(group_id, now.date().isoformat())
            await session.commit()

    async def _list_messages(self, group_id: int, *, since: datetime, until: datetime):
        try:
            from nonebot_plugin_qguard.models.base import get_session as get_qguard_session
            from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo
        except Exception:
            return []

        async with get_qguard_session() as session:
            return await MessageCacheRepo(session).list_group_messages(
                group_id,
                since=since,
                until=until,
                limit=max(100, self.config.qfun_wordcloud_message_limit),
            )


def tokenize_text(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    counter: Counter[str] = Counter()
    working = cleaned
    for term in DOMAIN_TERMS:
        pattern = re.compile(re.escape(term), flags=re.IGNORECASE)
        matches = pattern.findall(working)
        if matches:
            counter[term] += len(matches)
            working = pattern.sub(" ", working)

    for token in re.findall(r"[A-Za-z][A-Za-z0-9_+\-.]{1,}", working):
        normalized = token.strip(".-_+")
        if len(normalized) >= 2:
            counter[normalized.upper() if normalized.lower() in {"adb", "usb"} else normalized] += 1

    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", working):
        for token in _split_chinese_chunk(chunk):
            counter[token] += 1

    return [word for word, count in counter.items() for _ in range(count) if _is_meaningful(word)]


def format_wordcloud(result: WordCloudResult) -> str:
    title = f"QFun {result.period.label}词云"
    if not result.terms:
        return f"{title}\n这段时间还没有足够的聊天内容，先聊起来再看词云。"

    top_count = max(term.count for term in result.terms)
    lines = [
        title,
        f"统计：{result.message_count} 条消息，{result.user_count} 位群友，{len(result.terms)} 个关键词",
        "",
    ]
    for index, term in enumerate(result.terms[:20], start=1):
        width = max(1, round(term.count / top_count * 10))
        lines.append(f"{index:02d}. {term.word} {'█' * width} {term.count}")
    lines.append("")
    lines.append("今日话题：" + "、".join(term.word for term in result.terms[:5]))
    return "\n".join(lines)


def resolve_period(period_text: str | None = None, *, now: datetime | None = None) -> WordCloudPeriod:
    now = now or datetime.now()
    raw = (period_text or "今日").strip().lower()
    if raw in {"", "今日", "今天", "day", "today"}:
        start = datetime.combine(now.date(), time.min)
        return WordCloudPeriod("今日", "今日", start, now)
    if raw in {"昨日", "昨天", "yesterday"}:
        day = now.date() - timedelta(days=1)
        return WordCloudPeriod("昨日", "昨日", datetime.combine(day, time.min), datetime.combine(now.date(), time.min))
    match = re.fullmatch(r"(\d+)\s*(d|day|days|天)", raw)
    if match:
        days = min(max(int(match.group(1)), 1), 30)
        return WordCloudPeriod(f"{days}天", f"{days}天", now - timedelta(days=days), now)
    match = re.fullmatch(r"(\d+)\s*(h|hour|hours|小时|时)", raw)
    if match:
        hours = min(max(int(match.group(1)), 1), 72)
        return WordCloudPeriod(f"{hours}小时", f"{hours}小时", now - timedelta(hours=hours), now)
    raise ValueError("统计范围只支持：今日、昨日、7天、24小时。")


def parse_schedule_time(text: str | None) -> str:
    raw = (text or "").strip()
    match = re.fullmatch(r"([01]?\d|2[0-3])[:：]([0-5]\d)", raw)
    if not match:
        raise ValueError("时间格式不对，用法示例：/娱乐 词云定时 开 21:30")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _split_chinese_chunk(chunk: str) -> list[str]:
    if len(chunk) <= 4:
        return [chunk]
    result = []
    for size in (4, 3, 2):
        for index in range(0, len(chunk) - size + 1):
            result.append(chunk[index : index + size])
    return result


def _clean_text(text: str) -> str:
    text = re.sub(r"\[CQ:[^\]]+\]", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\d{5,}", " ", text)
    text = re.sub(r"[@#][^\s]+", " ", text)
    return text.strip()


def _is_meaningful(word: str) -> bool:
    if len(word) < 2:
        return False
    if word in STOPWORDS:
        return False
    if word.isdigit():
        return False
    return True


def _safe_load_config() -> Config:
    try:
        return load_config()
    except ValueError:
        return Config()
