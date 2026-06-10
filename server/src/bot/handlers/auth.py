# src/bot/handlers/auth.py
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
import httpx

from src.config import settings
from src.logging import get_logger

router = Router()
log = get_logger()


@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, bot: Bot):
    """
    Обработка deeplink от сайта
    Формат: /start auth_{session_token}
    """
    # Получаем параметр после start
    deep_link_param = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    if not deep_link_param.startswith("auth_"):
        await message.answer("Неверная ссылка авторизации")
        return
    
    session_token = deep_link_param.replace("auth_", "")
    
    # Отправляем запрос на сервер для подтверждения
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.API_DOMAIN_URL}/v1/auth/telegram/callback",
                json={
                    "session_token": session_token,
                    "tg_user_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                },
            )
            
            if response.status_code == 200:
                await message.answer(
                    "✅ Авторизация успешна!\n\n"
                    "Теперь вы можете вернуться на сайт."
                )
            else:
                await message.answer("❌ Ошибка авторизации. Попробуйте ещё раз.")
    
    except Exception as e:
        log.error(f"Error in telegram auth callback: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте ещё раз.")