"""Модуль для обработки исключений и отправки ошибок разработчикам"""

import traceback
from datetime import datetime
from pathlib import Path
from loguru import logger
from src.bot.settings.settings import DEVELOPER_IDS


async def send_error_to_developers(exception: Exception, traceback_text: str = None):
    """
    Отправляет сообщение об ошибке разработчикам в личные сообщения.
    
    :param exception: Exception: Исключение, которое произошло
    :param traceback_text: str: Текст traceback (если None, будет сформирован автоматически)
    """
    if not DEVELOPER_IDS:
        logger.warning("DEVELOPER_IDS не настроен, ошибки не будут отправлены разработчикам")
        return
    
    # Формируем traceback, если он не передан
    if traceback_text is None:
        traceback_text = "".join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))
    
    error_message = (
        f"⚠️ <b>Ошибка в боте</b>\n\n"
        f"<b>Тип ошибки:</b> {type(exception).__name__}\n"
        f"<b>Сообщение:</b> {str(exception)}\n\n"
        f"<b>Traceback:</b>\n<code>{traceback_text[:3000]}</code>"
    )
    
    # Сохраняем полный traceback в файл
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    traceback_file = Path("logs") / f"traceback_{timestamp}.txt"
    traceback_file.parent.mkdir(exist_ok=True)
    traceback_file.write_text(traceback_text, encoding="utf-8")
    
    # Отправляем сообщение каждому разработчику
    # используем lazy import чтобы избежать циклического импорта
    from src.bot.loader import bot
    
    for developer_id in DEVELOPER_IDS:
        try:
            # Отправляем текстовое сообщение
            await bot.send_message(
                chat_id=developer_id,
                text=error_message,
                parse_mode="HTML"
            )
            
            # Отправляем файл с traceback
            with open(traceback_file, "rb") as file:
                await bot.send_document(
                    chat_id=developer_id,
                    document=file,
                    caption=f"Полный traceback для ошибки: {type(exception).__name__}"
                )
        except Exception as e:
            logger.error(f"Не удалось отправить ошибку разработчику {developer_id}: {e}")

