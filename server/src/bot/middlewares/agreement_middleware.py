"""
middleware для проверки согласия 152-ФЗ
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from src.bot.database.methods import check_user_agreement


class AgreementMiddleware(BaseMiddleware):
    """middleware проверки согласия на обработку ПД"""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # пропускаем команду /start и другие команды, которые должны обрабатываться без проверки
        if isinstance(event, Message):
            if event.text:
                # Команды, которые должны проходить без проверки согласия
                allowed_commands = ['/start', '/help', '/rules', '/cancel', '/oferta']
                if any(event.text == cmd or event.text.startswith(cmd + ' ') for cmd in allowed_commands):
                    return await handler(event, data)
        
        if isinstance(event, CallbackQuery):
            # Callback'и, которые должны проходить без проверки согласия
            if event.data and (event.data.startswith('agree_') or 
                              event.data == 'return_to_oferta' or 
                              event.data == 'check_subscription'):
                return await handler(event, data)
        
        # проверяем согласие
        user_id = event.from_user.id
        agreed = await check_user_agreement(user_id)
        
        if not agreed:
            # если не согласился - ничего не делаем
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Для использования бота необходимо принять условия обработки ПД",
                    show_alert=True
                )
            elif isinstance(event, Message):
                await event.answer(
                    "⚠️ Для использования бота сначала примите соглашение через /start"
                )
            return
        
        return await handler(event, data)
