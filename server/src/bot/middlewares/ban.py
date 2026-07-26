"""Ban middleware — blocks banned users from interacting with the bot."""
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

_banned_cache: set[int] = set()
_banned_cache_time: float = 0
BANNED_CACHE_TTL = 30


async def _get_banned_user_ids() -> set[int]:
    global _banned_cache, _banned_cache_time
    now = time.monotonic()
    if now - _banned_cache_time < BANNED_CACHE_TTL and _banned_cache:
        return _banned_cache
    from src.kit.database.service import database_service
    from src.models import Blacklist
    from sqlalchemy import select

    async with database_service.get_session() as session:
        result = await session.execute(select(Blacklist.tg_user_id))
        _banned_cache = set(result.scalars().all())
    _banned_cache_time = now
    return _banned_cache


def invalidate_banned_cache():
    global _banned_cache_time
    _banned_cache_time = 0


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        # Allow /start so banned users can see the ban message
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        banned_ids = await _get_banned_user_ids()
        if user.id in banned_ids:
            if isinstance(event, CallbackQuery):
                await event.answer("Ваш аккаунт заблокирован.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("Ваш аккаунт заблокирован. Обратитесь к администрации.")
            return

        return await handler(event, data)
