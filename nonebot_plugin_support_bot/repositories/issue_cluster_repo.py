from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_support_bot.models import SupportIssueCluster


class SupportIssueClusterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_key(self, cluster_key: str) -> SupportIssueCluster | None:
        result = await self.session.scalars(
            select(SupportIssueCluster).where(SupportIssueCluster.cluster_key == cluster_key)
        )
        return result.one_or_none()

    async def record(
        self,
        *,
        cluster_key: str,
        title: str,
        skill: str,
        issue_type: str,
        question: str,
        group_id: int,
        user_id: int,
        no_answer: bool = False,
        unresolved: bool = False,
        resolved: bool = False,
        record_no: str = "",
    ) -> SupportIssueCluster:
        item = await self.get_by_key(cluster_key)
        if item is None:
            item = SupportIssueCluster(
                cluster_key=cluster_key,
                title=title[:256],
                skill=skill[:64],
                issue_type=issue_type[:64],
                example_question=question[:1000],
            )
            self.session.add(item)
        item.last_question = question[:1000]
        item.last_group_id = group_id
        item.last_user_id = user_id
        item.occurrence_count = int(item.occurrence_count or 0) + 1
        if no_answer:
            item.no_answer_count = int(item.no_answer_count or 0) + 1
        if unresolved:
            item.unresolved_count = int(item.unresolved_count or 0) + 1
        if resolved:
            item.resolved_count = int(item.resolved_count or 0) + 1
        if record_no:
            item.last_record_no = record_no[:64]
        item.updated_at = datetime.utcnow()
        await self.session.flush()
        return item

    async def list_hot(self, limit: int = 5) -> list[SupportIssueCluster]:
        result = await self.session.scalars(
            select(SupportIssueCluster)
            .order_by(
                desc(SupportIssueCluster.unresolved_count),
                desc(SupportIssueCluster.no_answer_count),
                desc(SupportIssueCluster.occurrence_count),
                desc(SupportIssueCluster.updated_at),
            )
            .limit(limit)
        )
        return list(result)
