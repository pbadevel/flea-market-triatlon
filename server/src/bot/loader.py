"""Файл - с настройками бота"""

from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout
from loguru import logger
from aiogram import Dispatcher
from src.bot.middlewares.auth_middleware import AuthMiddleware
from src.bot.middlewares.logging_middleware import LoggingMiddleware
from src.bot.middlewares.throttle_middleware import ThrottleMiddleware
from src.config import settings

# Импортируем logging_config для инициализации loguru
import src.bot.logging_config
session = AiohttpSession(timeout=ClientTimeout(total=60))
storage = MemoryStorage()
bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
dp = Dispatcher(storage=storage)
dp.message.middleware(LoggingMiddleware())

# dp.message.middleware(AuthMiddleware()) TODO: Если необходимо добавить мидлвейр для прав
# dp.message.middleware(ThrottleMiddleware()) TODO: Если необходимо добавить мидлвейр для ограничения частоты запросов от пользователя
