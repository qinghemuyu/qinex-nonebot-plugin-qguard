from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nonebot_plugin_qguard.enums import QGuardRole
from nonebot_plugin_qguard.models.member_profile import MemberProfile


class MemberRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: int, user_id: int) -> MemberProfile | None:
        result = await self.session.scalars(
            select(MemberProfile).where(MemberProfile.group_id == group_id, MemberProfile.user_id == user_id)
        )
        return result.one_or_none()

    async def get_or_create(self, group_id: int, user_id: int) -> MemberProfile:
        profile = await self.get(group_id, user_id)
        if profile is None:
            profile = MemberProfile(group_id=group_id, user_id=user_id)
            self.session.add(profile)
            await self.session.flush()
        return profile

    async def set_role(self, group_id: int, user_id: int, role: QGuardRole) -> MemberProfile:
        profile = await self.get_or_create(group_id, user_id)
        profile.role = int(role)
        await self.session.flush()
        return profile

    async def add_warning(self, group_id: int, user_id: int, score_delta: int = 1) -> MemberProfile:
        profile = await self.get_or_create(group_id, user_id)
        profile.warning_count += 1
        profile.warning_score += score_delta
        await self.session.flush()
        return profile

    async def add_mute(self, group_id: int, user_id: int) -> MemberProfile:
        profile = await self.get_or_create(group_id, user_id)
        profile.mute_count += 1
        await self.session.flush()
        return profile

    async def add_kick(self, group_id: int, user_id: int) -> MemberProfile:
        profile = await self.get_or_create(group_id, user_id)
        profile.kick_count += 1
        await self.session.flush()
        return profile
