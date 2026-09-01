from aiogram import BaseMiddleware
from aiogram.types import Update
from typing import Callable, Dict, Any, Awaitable
from src.bot.database.methods import async_session
from src.models import User
from sqlalchemy.future import select


class AuthMiddleware(BaseMiddleware):
    """
    Мидлвейр для проверки авторизации пользователей перед доступом к определенным командам или хендлерам.

    Этот мидлвейр проверяет, существует ли пользователь в базе данных по его telegram_id.
    Если пользователь не авторизован (не найден в базе), ему отправляется уведомление,
    и доступ к хендлеру ограничивается.

    Методы:
        - is_user_authorized: Проверяет авторизацию пользователя, выполняя поиск в базе данных.
        - __call__: Основной метод мидлвейра, который перехватывает событие, проверяет авторизацию
                    и блокирует выполнение хендлера, если пользователь не авторизован.
    """

    def __init__(self):
        """Инициализирует AuthMiddleware."""
        super().__init__()

    async def is_user_authorized(self, telegram_id: int) -> bool:
        """
        Проверяет, авторизован ли пользователь, выполняя поиск в базе данных по его Telegram ID.

        Аргументы:
            telegram_id (int): Telegram ID пользователя.

        Возвращает:
            bool: True, если пользователь найден в базе, иначе False.
        """
        async with async_session() as session:
            result = await session.execute(select(User).where(User.tg_user_id == telegram_id))
            user = result.scalars().first()
            return user is not None

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Метод мидлвейра, который перехватывает каждое событие, проверяет авторизацию пользователя
        и в зависимости от результата либо допускает, либо блокирует доступ к хендлеру.

        Аргументы:
            handler (Callable[[Update, Dict[str, Any]], Awaitable[Any]]): Следующий хендлер для выполнения.
            event (Update): Входящее событие обновления.
            data (Dict[str, Any]): Дополнительные данные, передаваемые в хендлер.

        Возвращает:
            Any: Результат выполнения хендлера, если пользователь авторизован; иначе None.
        """
        telegram_id = event.message.from_user.id if event.message else None
        if telegram_id:
            is_authorized = await self.is_user_authorized(telegram_id)
            if not is_authorized:
                await event.message.reply("Вы не авторизованы для использования этой команды.")
                return

        return await handler(event, data)
