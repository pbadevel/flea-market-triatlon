from aiogram import types, Dispatcher, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.bot.loader import logger, bot
from src.models import *


async def delete_message(user_id: int, session: AsyncSession) -> None:
    """
    Асинхронно удаляет сообщения из чата по заданному user_id.

    Функция находит сообщения для удаления, хранящиеся в базе данных с моделью DeleteMessage.
    Если идентификатор сообщения содержит '&', он обрабатывается как несколько идентификаторов,
    разделённых '&', и удаляется каждый из них. В случае ошибки при удалении любого сообщения,
    ошибка логируется, но не прерывает выполнение цикла удаления.

    :param user_id: int: Идентификатор пользователя, для которого выполняется удаление сообщений.
    :param session: AsyncSession: Асинхронная сессия для выполнения запросов SQLAlchemy.
    """
    try:
        result = await session.execute(select(DeleteMessage).where(DeleteMessage.chat_id == user_id))
        messages = result.scalars().all()

        for mess in messages:
            if '&' in mess.message_id:
                mes_ids = mess.message_id.split('&')
                for elem in mes_ids:
                    try:
                        await bot.delete_message(chat_id=mess.chat_id, message_id=int(elem))
                    except Exception as e:
                        logger.warning(f"Не удалось удалить сообщение {elem} для чата {mess.chat_id}", exc_info=e)
            else:
                try:
                    await bot.delete_message(chat_id=mess.chat_id, message_id=int(mess.message_id))
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение {mess.message_id} для чата {mess.chat_id}",
                                   exc_info=e)

            await session.delete(mess)
        await session.commit()

    except Exception as error:
        logger.error('В работе бота возникло исключение', exc_info=error)


async def echo_handler(message: types.Message) -> None:
    """
    Удаляет полученное сообщение.

    Функция предназначена для немедленного удаления сообщения, которое отправлено боту.
    Используется, чтобы не сохранять ненужные сообщения в чате с ботом.

    :param message: types.Message: Сообщение, которое будет удалено.
    """
    # Не удаляем команды - они должны обрабатываться специальными обработчиками
    if message.text and message.text.startswith('/'):
        return
    await message.delete()


def register_echo_handlers(dp: Dispatcher) -> None:
    # Регистрируем echo handler для всех текстовых сообщений
    # В самом обработчике проверяем, не является ли сообщение командой
    dp.message.register(echo_handler, F.text)
