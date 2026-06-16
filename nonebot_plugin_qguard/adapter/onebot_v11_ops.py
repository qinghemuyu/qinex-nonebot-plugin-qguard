from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.exception import ActionFailed, NetworkError

from .group_ops import GroupOps

T = TypeVar("T")


class QGuardActionError(RuntimeError):
    pass


class OneBotV11GroupOps(GroupOps):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _call(self, func: Callable[..., Awaitable[T]], **kwargs: Any) -> T:
        try:
            return await func(**kwargs)
        except (ActionFailed, NetworkError) as exc:
            raise QGuardActionError(str(exc)) from exc

    async def send_group_msg(self, group_id: int, message: str) -> Any:
        return await self._call(self.bot.send_group_msg, group_id=group_id, message=message)

    async def delete_msg(self, message_id: int) -> None:
        await self._call(self.bot.delete_msg, message_id=message_id)

    async def get_msg(self, message_id: int) -> dict[str, Any]:
        return await self._call(self.bot.get_msg, message_id=message_id)

    async def mute(self, group_id: int, user_id: int, seconds: int) -> None:
        await self._call(self.bot.set_group_ban, group_id=group_id, user_id=user_id, duration=seconds)

    async def unmute(self, group_id: int, user_id: int) -> None:
        await self._call(self.bot.set_group_ban, group_id=group_id, user_id=user_id, duration=0)

    async def kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> None:
        await self._call(
            self.bot.set_group_kick,
            group_id=group_id,
            user_id=user_id,
            reject_add_request=reject_add_request,
        )

    async def whole_mute(self, group_id: int, enable: bool) -> None:
        await self._call(self.bot.set_group_whole_ban, group_id=group_id, enable=enable)

    async def set_group_card(self, group_id: int, user_id: int, card: str) -> None:
        await self._call(self.bot.set_group_card, group_id=group_id, user_id=user_id, card=card)

    async def set_group_name(self, group_id: int, name: str) -> None:
        await self._call(self.bot.set_group_name, group_id=group_id, group_name=name)

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool) -> None:
        await self._call(self.bot.set_group_admin, group_id=group_id, user_id=user_id, enable=enable)

    async def set_group_anonymous(self, group_id: int, enable: bool) -> None:
        await self._call(self.bot.set_group_anonymous, group_id=group_id, enable=enable)

    async def set_special_title(self, group_id: int, user_id: int, title: str, duration: int = -1) -> None:
        await self._call(
            self.bot.set_group_special_title,
            group_id=group_id,
            user_id=user_id,
            special_title=title,
            duration=duration,
        )

    async def get_group_info(self, group_id: int, no_cache: bool = True) -> dict[str, Any]:
        return await self._call(self.bot.get_group_info, group_id=group_id, no_cache=no_cache)

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = True) -> dict[str, Any]:
        return await self._call(
            self.bot.get_group_member_info,
            group_id=group_id,
            user_id=user_id,
            no_cache=no_cache,
        )

    async def get_group_member_list(self, group_id: int) -> list[dict[str, Any]]:
        return await self._call(self.bot.get_group_member_list, group_id=group_id)

    async def handle_group_add_request(self, flag: str, sub_type: str, approve: bool, reason: str = "") -> None:
        await self._call(
            self.bot.set_group_add_request,
            flag=flag,
            sub_type=sub_type,
            approve=approve,
            reason=reason,
        )
