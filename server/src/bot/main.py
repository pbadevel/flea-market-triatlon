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
    
    # Register handlers
    from src.bot.handlers import moderation
    from src.bot.handlers import auth as auth_handler

    dp.include_router(moderation.router)
    dp.include_router(auth_handler.router)
    
    return dp


# Global instances
bot = create_bot()
dp = create_dispatcher()


async def setup_bot():
    """Setup bot (called in lifespan)"""
    log.info("Setting up Telegram bot...")
    # Для тестов используем polling вместо webhook
    log.info("Telegram bot ready (polling mode for tests)")


async def shutdown_bot():
    """Shutdown bot"""
    log.info("Shutting down Telegram bot...")
    await bot.session.close()
    log.info("Telegram bot stopped")


async def process_update_manually(update_data: dict):
    """
    Process update manually (for testing without webhook)
    Can be called from API endpoint
    """
    from aiogram.types import Update
    update = Update(**update_data)
    await dp.feed_update(bot, update)


# from aiogram import Bot, Dispatcher
# from aiogram.enums import ParseMode
# from aiogram.client.default import DefaultBotProperties
# from aiogram.fsm.storage.memory import MemoryStorage

# from src.config import settings
# from src.logging import get_logger

# log = get_logger()


# def create_bot() -> Bot:
#     """Create Telegram bot instance"""
#     return Bot(
#         token=settings.BOT_TOKEN,
#         default=DefaultBotProperties(parse_mode=ParseMode.HTML),
#     )


# def create_dispatcher() -> Dispatcher:
#     """Create dispatcher with FSM storage"""
#     storage = MemoryStorage()
#     dp = Dispatcher(storage=storage)
    
#     # Register handlers
#     from src.bot.handlers import moderation
#     dp.include_router(moderation.router)
    
#     return dp


# # Global instances
# bot = create_bot()
# dp = create_dispatcher()


# async def setup_bot():
#     """Setup bot (called in lifespan)"""
#     log.info("Setting up Telegram bot...")
#     # Webhook will be set separately
#     log.info("Telegram bot ready")


# async def shutdown_bot():
#     """Shutdown bot"""
#     log.info("Shutting down Telegram bot...")
#     await bot.session.close()
#     log.info("Telegram bot stopped")