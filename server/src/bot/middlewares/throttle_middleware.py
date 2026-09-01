"""
ThrottlingMiddleware: бан по tg id — бот не реагирует на пользователей из черного списка в БД.
Троттлинг (ограничение частоты) отключён.
"""

from typing import Any, Awaitable, Callable, Dict
import time

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

# Кэш списка забаненных tg_id (обновляется раз в 30 сек)
_banned_cache: set[int] = set()
_banned_cache_time: float = 0
BANNED_CACHE_TTL = 30


async def _get_banned_user_ids() -> set[int]:
    """Возвращает множество tg_user_id из черного списка (с кэшем)."""
    global _banned_cache, _banned_cache_time
    now = time.monotonic()
    if now - _banned_cache_time < BANNED_CACHE_TTL and _banned_cache is not None:
        return _banned_cache
    from src.bot.database.methods import get_banned_tg_ids
    _banned_cache = await get_banned_tg_ids()
    _banned_cache_time = now
    return _banned_cache


def invalidate_banned_cache():
    """Сбросить кэш черного списка (вызывать после бана/разбана)."""
    global _banned_cache_time
    _banned_cache_time = 0


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        banned_ids = await _get_banned_user_ids()
        if user.id in banned_ids:
            return

        return await handler(event, data)


# Совместимость с loader (если раскомментируют ThrottleMiddleware)
ThrottleMiddleware = ThrottlingMiddleware
