import traceback
from aiogram import BaseMiddleware
from aiogram.types import Update
from typing import Callable, Dict, Any, Awaitable
from loguru import logger
from src.bot.utils.error_handler import send_error_to_developers


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования входящих событий и команд от пользователей.

    Этот мидлвар логирует каждый запрос пользователя, включая сообщения и команды.
    Полезен для мониторинга и диагностики работы бота.

    Методы:
        - __call__: Обрабатывает каждое событие и логирует его с подробной информацией.
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Основной метод мидлвара, логирующий событие перед его обработкой.

        Логирует ID пользователя, тип события, его содержание и результат выполнения хендлера.

        Аргументы:
            handler (Callable[[Update, Dict[str, Any]], Awaitable[Any]]): Следующий хендлер для выполнения.
            event (Update): Входящее событие обновления.
            data (Dict[str, Any]): Дополнительные данные, передаваемые в хендлер.

        Возвращает:
            Any: Результат выполнения хендлера.
        """
        # определяем тип события
        from aiogram.types import Message, CallbackQuery
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            message_text = event.text or "Не сообщение"
            callback_data = None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            message_text = "Callback"
            callback_data = event.data
            logger.info(f"🟢 CALLBACK_QUERY получен! User: {user_id}, Data: {callback_data}, Chat: {event.message.chat.id if event.message else 'N/A'}")
        else:
            # для Update объекта
            message = getattr(event, 'message', None)
            callback_query = getattr(event, 'callback_query', None)
            user_id = message.from_user.id if message and message.from_user else (callback_query.from_user.id if callback_query and callback_query.from_user else None)
            message_text = message.text if message else "Не сообщение"
            callback_data = callback_query.data if callback_query else None
            if callback_query:
                logger.info(f"🟢 CALLBACK_QUERY в Update! User: {user_id}, Data: {callback_data}, Chat: {callback_query.message.chat.id if callback_query.message else 'N/A'}")

        logger.info(
            f"Получено событие от пользователя {user_id}: "
            f"Текст сообщения - '{message_text}', Данные callback - '{callback_data}'"
        )

        try:
            result = await handler(event, data)
            logger.info(f"Событие от пользователя {user_id} обработано успешно.")
            return result
        except Exception as e:
            # Формируем traceback
            traceback_text = "".join(traceback.format_exception(
                type(e),
                e,
                e.__traceback__
            ))
            
            # Логируем ошибку
            logger.error(
                f"Ошибка при обработке события от пользователя {user_id}: {str(e)}\n{traceback_text}"
            )
            
            # Отправляем ошибку разработчикам
            await send_error_to_developers(e, traceback_text)
            
            raise e
