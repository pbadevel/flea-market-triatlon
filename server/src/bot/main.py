"""src/bot/main.py - УПРОЩЕННАЯ ВЕРСИЯ БЕЗ WEBHOOK"""
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.logging import get_logger

log = get_logger()


def create_bot() -> Bot:
    """Create Telegram bot instance"""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create dispatcher with FSM storage"""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register middleware
    from src.bot.middlewares.ban import BanMiddleware
    from src.bot.middlewares.agreement import AgreementMiddleware
    dp.message.middleware(BanMiddleware())
    dp.callback_query.middleware(BanMiddleware())
    dp.message.middleware(AgreementMiddleware())
    dp.callback_query.middleware(AgreementMiddleware())
    
    # Register handlers (order matters!) 
    from src.bot.handlers import start as start_handler
    from src.bot.handlers import add_ad
    from src.bot.handlers import catalog
    from src.bot.handlers import my_ads
    from src.bot.handlers import reviews
    from src.bot.handlers import moderation
    from src.bot.handlers import admin as admin_handler
    from src.bot.handlers import admin_panel
    from src.bot.handlers import echo

    dp.include_router(start_handler.router)
    dp.include_router(add_ad.router)
    dp.include_router(catalog.router)
    dp.include_router(my_ads.router)
    dp.include_router(reviews.router)
    dp.include_router(moderation.router)
    dp.include_router(admin_handler.router)
    dp.include_router(admin_panel.router)
    dp.include_router(echo.router)  # echo always last
    
    return dp


# Global instances — создаются только при старте (не при импорте)
_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = create_bot()
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = create_dispatcher()
    return _dp


async def setup_bot():
    """Setup bot (called in lifespan)"""
    log.info("Setting up Telegram bot...")
    bot = get_bot()
    dp = get_dispatcher()
    
    # Error handler
    @dp.errors()
    async def error_handler(event):
        from aiogram.types import ErrorEvent
        import traceback
        exception = event.exception
        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        log.error(f"Bot error: {type(exception).__name__}: {exception}\n{tb}")
        
        # Notify developers
        for dev_id in settings.DEVELOPER_IDS:
            try:
                await bot.send_message(dev_id, f"Bot error:\n{type(exception).__name__}: {exception}")
            except Exception:
                pass
        return True
    
    log.info("Telegram bot ready (polling mode)")
    
    # Set bot commands
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="cancel", description="Отмена"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="rules", description="Правила"),
        BotCommand(command="oferta", description="Оферта"),
        BotCommand(command="admin", description="Админ-панель"),
    ])
    
    print("@", (await bot.me()).username, sep='')
    await dp.start_polling(bot)


async def shutdown_bot():
    """Shutdown bot"""
    log.info("Shutting down Telegram bot...")
    bot = get_bot()
    await bot.session.close()
    log.info("Telegram bot stopped")


async def process_update_manually(update_data: dict):
    """
    Process update manually (for testing without webhook)
    Can be called from API endpoint
    """
    from aiogram.types import Update
    update = Update(**update_data)
    await get_dispatcher().feed_update(get_bot(), update)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(setup_bot())
    except Exception as e:
        print("Failed bot: {e}".format(e))