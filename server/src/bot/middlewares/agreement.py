"""Agreement middleware — 152-ФЗ compliance. Users must accept privacy policy."""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class AgreementMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Allow commands that don't require agreement
        if isinstance(event, Message) and event.text:
            allowed = ["/start", "/help", "/rules", "/cancel", "/oferta"]
            if any(event.text == cmd or event.text.startswith(cmd + " ") for cmd in allowed):
                return await handler(event, data)

        # Allow agreement-related callbacks
        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith("agree_") or event.data == "return_to_oferta":
                return await handler(event, data)

        # Check agreement
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        from src.kit.database.service import database_service
        from src.models import User
        from sqlalchemy import select

        async with database_service.get_session() as session:
            result = await session.execute(
                select(User).where(User.tg_user_id == user.id)
            )
            db_user = result.scalar_one_or_none()

        if db_user and not db_user.agreed_to_terms:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "Для использования бота необходимо принять условия обработки ПД. Нажмите /start",
                    show_alert=True,
                )
            elif isinstance(event, Message):
                await event.answer(
                    "Для использования бота сначала примите соглашение через /start"
                )
            return

        return await handler(event, data)
