from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from nonebot_plugin_qfun.models import init_db as init_qfun_db
from nonebot_plugin_qfun.services.wordcloud_service import (
    QFunService,
    format_wordcloud,
    parse_schedule_time,
    resolve_period,
    tokenize_text,
)
from nonebot_plugin_qguard.models.base import get_session as get_qguard_session
from nonebot_plugin_qguard.models.message_cache import MessageCache
from nonebot_plugin_qguard.repositories.message_cache_repo import MessageCacheRepo


def test_qfun_tokenize_prefers_qinex_terms() -> None:
    tokens = tokenize_text("上位机遮罩打开后，键盘输出会同步到电脑，映射和压枪都在聊")

    assert "上位机" in tokens
    assert "遮罩" in tokens
    assert "键盘" in tokens
    assert "映射" in tokens
    assert "压枪" in tokens


def test_qfun_period_and_schedule_time_parsers() -> None:
    now = datetime(2026, 6, 20, 12, 0)
    today = resolve_period("今日", now=now)
    seven_days = resolve_period("7天", now=now)

    assert today.since == datetime(2026, 6, 20, 0, 0)
    assert today.until == now
    assert seven_days.since == now - timedelta(days=7)
    assert parse_schedule_time("9:05") == "09:05"


@pytest.mark.asyncio
async def test_qfun_wordcloud_from_message_cache() -> None:
    await init_qfun_db()
    group_id = 991000000 + (uuid4().int % 1000000)
    now = datetime(2026, 6, 20, 22, 0)
    messages = [
        MessageCache(
            message_id=9100001 + index + (uuid4().int % 1000000),
            group_id=group_id,
            user_id=1000 + index,
            plain_text=text,
            raw_message_json="[]",
            expires_at=now + timedelta(days=1),
            created_at=now - timedelta(minutes=index + 1),
        )
        for index, text in enumerate(
            [
                "上位机遮罩打开了，键盘同步输出导致电脑乱动",
                "映射校准之后上位机还是卡顿",
                "压枪和连点今天讨论很多，映射也很多",
                "/娱乐 词云 今日",
            ]
        )
    ]
    async with get_qguard_session() as session:
        repo = MessageCacheRepo(session)
        for item in messages:
            await repo.upsert(item)
        await session.commit()

    result = await QFunService().build_wordcloud(group_id, "今日", now=now)
    rendered = format_wordcloud(result)

    assert result.message_count == 3
    assert result.user_count == 3
    assert "上位机" in rendered
    assert "映射" in rendered
    assert "QFun 今日词云" in rendered


@pytest.mark.asyncio
async def test_qfun_wordcloud_schedule_due_once() -> None:
    await init_qfun_db()
    group_id = 992000000 + (uuid4().int % 1000000)
    service = QFunService()

    result = await service.set_wordcloud_schedule(
        group_id,
        enabled=True,
        schedule_time="21:30",
        period_text="今日",
        operator_id=1348984838,
    )
    due = await service.due_wordcloud_messages(datetime(2026, 6, 20, 21, 30))
    await service.mark_wordcloud_sent(group_id, datetime(2026, 6, 20, 21, 30))
    due_again = await service.due_wordcloud_messages(datetime(2026, 6, 20, 21, 30))

    assert "每日词云已开启" in result
    assert any(item[0] == group_id for item in due)
    assert not any(item[0] == group_id for item in due_again)
