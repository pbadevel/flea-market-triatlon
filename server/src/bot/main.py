"""Файл - запуск бота"""

import traceback
from aiogram.types import BotCommand
# from src.bot.database.methods import init_db
from src.bot.loader import dp, bot
from src.bot.handlers import start, echo
import asyncio
from src.bot.services.web_service.app import init_app as init_web_app
from aiohttp import web
from loguru import logger
from src.bot.utils.error_handler import send_error_to_developers
from src.bot.middlewares.agreement_middleware import AgreementMiddleware

# импортируем настроенный loguru
import src.bot.logging_config


async def set_default_commands():
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="cancel", description="Отмена"),
            BotCommand(command="help", description="Помощь (Инструкция и Написать админу)"),
            BotCommand(command="rules", description="Правила"),
            BotCommand(command="oferta", description="Оферта"),
        ]
    )


def setup_error_handlers():
    """
    Настраивает обработчики ошибок для aiogram.
    """
    from aiogram import types
    
    @dp.errors()
    async def error_handler(event: types.ErrorEvent):
        """
        Обработчик ошибок aiogram.
        """
        exception = event.exception
        
        # Формируем traceback
        traceback_text = "".join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))
        
        # Логируем ошибку
        logger.error(
            f"Ошибка при обработке обновления: {type(exception).__name__}: {exception}\n{traceback_text}"
        )
        
        # Отправляем разработчикам
        await send_error_to_developers(exception, traceback_text)
        
        # Возвращаем True, чтобы показать, что ошибка обработана
        return True


async def main():
    # настройка обработчиков ошибок
    setup_error_handlers()
    
    # await bot.delete_webhook(drop_pending_updates=True)

    # await init_db()
    
    # middleware
    from src.bot.middlewares.throttle_middleware import ThrottlingMiddleware
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(AgreementMiddleware())
    dp.callback_query.middleware(AgreementMiddleware())
    
    # регистрируем обработчики
    start.register_start_handlers(dp)
    
    from src.bot.handlers import add_ad, moderation, catalog, support, admin, admin_panel, my_ads
    add_ad.register_add_ad_handlers(dp)
    moderation.register_moderation_handlers(dp)
    my_ads.register_my_ads_handlers(dp)  # Регистрируем раньше catalog для правильной обработки "back"
    catalog.register_catalog_handlers(dp)
    support.register_support_handlers(dp)
    admin.register_admin_handlers(dp)
    admin_panel.register_admin_panel_handlers(dp)
    
    # echo последним
    echo.register_echo_handlers(dp)
    
    await set_default_commands()

    # Запускаем фоновый планировщик поднятий
    from src.bot.services.scheduler import run_scheduler
    asyncio.create_task(run_scheduler())
    
    logger.info("бот запущен и готов к работе")

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
