from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.models.member_profile import MemberProfile
from nonebot_plugin_qguard.repositories.member_repo import MemberRepo


class ScoreRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_profile(self, group_id: int, user_id: int) -> MemberProfile:
        return await MemberRepo(self.session).get_or_create(group_id, user_id)

    async def add_score(self, group_id: int, user_id: int, delta: int) -> tuple[MemberProfile, int, int]:
        profile = await self.get_or_create_profile(group_id, user_id)
        previous_score = profile.warning_score
        profile.warning_score += delta
        await self.session.flush()
        return profile, previous_score, profile.warning_score

    async def reset_score(self, group_id: int, user_id: int) -> tuple[MemberProfile, int]:
        profile = await self.get_or_create_profile(group_id, user_id)
        previous_score = profile.warning_score
        profile.warning_score = 0
        await self.session.flush()
        return profile, previous_score
