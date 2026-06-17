from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_group_wiki.models import WikiArticle, WikiFeedback


class WikiFeedbackRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        article: WikiArticle,
        *,
        group_id: int | None,
        user_id: int | None,
        feedback_type: str,
        comment: str = "",
    ) -> WikiFeedback:
        feedback = WikiFeedback(
            article_id=article.id,
            group_id=group_id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment,
        )
        if feedback_type == "useful":
            article.useful_count += 1
        elif feedback_type == "useless":
            article.useless_count += 1
        self.session.add(feedback)
        await self.session.flush()
        return feedback
