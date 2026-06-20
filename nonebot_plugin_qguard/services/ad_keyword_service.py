from nonebot_plugin_qguard.enums import AuditAction, AuditResult
from nonebot_plugin_qguard.models.ad_keyword import AdKeyword
from nonebot_plugin_qguard.models.base import get_session
from nonebot_plugin_qguard.repositories.ad_keyword_repo import AdKeywordRepo
from nonebot_plugin_qguard.repositories.audit_log_repo import AuditLogRepo
from nonebot_plugin_qguard.services.ad_keyword_defaults import (
    DEFAULT_AD_KEYWORD_OPERATOR_ID,
    DEFAULT_AD_KEYWORDS,
)
from nonebot_plugin_qguard.services.result import ActionResult


class AdKeywordService:
    async def add(self, group_id: int, operator_id: int, keyword: str) -> ActionResult:
        keyword = keyword.strip()
        if not keyword:
            return ActionResult(success=False, action=str(AuditAction.ADD_AD_KEYWORD), message="广告词不能为空。")
        if len(keyword) > 64:
            return ActionResult(success=False, action=str(AuditAction.ADD_AD_KEYWORD), message="广告词不能超过 64 个字符。")

        async with get_session() as session:
            item, created = await AdKeywordRepo(session).add(group_id, keyword, operator_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.ADD_AD_KEYWORD,
                result=AuditResult.SUCCESS,
                metadata={"keyword_id": item.id, "keyword": keyword, "created": created},
            )
            await session.commit()
            return ActionResult(
                success=True,
                action=str(AuditAction.ADD_AD_KEYWORD),
                message=f"广告词已{'添加' if created else '重新启用'}：#{item.id} {item.keyword}",
            )

    async def ensure_defaults(self, group_id: int) -> int:
        async with get_session() as session:
            created = await AdKeywordRepo(session).add_missing(
                group_id,
                DEFAULT_AD_KEYWORDS,
                DEFAULT_AD_KEYWORD_OPERATOR_ID,
            )
            if created:
                await session.commit()
            return created

    async def remove(self, group_id: int, operator_id: int, keyword_id: int) -> ActionResult:
        async with get_session() as session:
            item = await AdKeywordRepo(session).disable(keyword_id, group_id)
            await AuditLogRepo(session).create(
                group_id=group_id,
                operator_id=operator_id,
                action=AuditAction.REMOVE_AD_KEYWORD,
                result=AuditResult.SUCCESS if item else AuditResult.SKIPPED,
                metadata={"keyword_id": keyword_id},
            )
            await session.commit()

        if item is None:
            return ActionResult(success=False, action=str(AuditAction.REMOVE_AD_KEYWORD), message="没有找到这个广告词。")
        return ActionResult(success=True, action=str(AuditAction.REMOVE_AD_KEYWORD), message=f"广告词 #{keyword_id} 已删除。")

    async def list(self, group_id: int, limit: int = 40, offset: int = 0) -> list[AdKeyword]:
        await self.ensure_defaults(group_id)
        async with get_session() as session:
            return await AdKeywordRepo(session).list_all(group_id, limit=limit, offset=offset)

    async def count(self, group_id: int) -> int:
        await self.ensure_defaults(group_id)
        async with get_session() as session:
            return await AdKeywordRepo(session).count_all(group_id)
