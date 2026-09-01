"""
система логирования на базе loguru с автоотправкой файлов
"""

import sys
from pathlib import Path
from loguru import logger
import asyncio
from functools import wraps


# убираем дефолтный обработчик
logger.remove()

# создаем папку
Path("logs").mkdir(exist_ok=True)


# === ФОРМАТЫ ===

# для терминала - красиво и читабельно
terminal_format = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[user_id]: <10}</cyan> | "
    "<level>{message}</level>"
)

# для файлов - полная инфа
file_format = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{extra[user_id]: <10} | "
    "{message}"
)


# === ТЕРМИНАЛ ===

logger.add(
    sys.stdout,
    format=terminal_format,
    level="INFO",
    colorize=True,
    filter=lambda record: record["extra"].setdefault("user_id", "SYSTEM")
)


# === ФУНКЦИЯ АВТООТПРАВКИ ===

async def send_log_to_admins(filepath: str):
    """отправка лог-файла админам при достижении 5 МБ"""
    try:
        from src.bot.loader import bot
        from src.bot.settings.settings import DEVELOPER_IDS
        from aiogram.types import FSInputFile
        
        file_path = Path(filepath)
        if not file_path.exists() or file_path.stat().st_size == 0:
            return
        
        for admin_id in DEVELOPER_IDS:
            try:
                document = FSInputFile(str(file_path))
                await bot.send_document(
                    chat_id=admin_id,
                    document=document,
                    caption=f"⚠️ файл {file_path.name} достиг 5 МБ"
                )
            except Exception as e:
                print(f"ошибка отправки админу {admin_id}: {e}")
    except Exception as e:
        print(f"ошибка автоотправки: {e}")


def rotation_callback(filepath: str):
    """callback при ротации - отправляем файл"""
    try:
        # создаем задачу в текущем event loop
        loop = asyncio.get_event_loop()
        loop.create_task(send_log_to_admins(filepath))
    except:
        # если event loop еще не запущен - пропускаем
        pass


# === ФАЙЛЫ ЛОГОВ ===

# 1. основной файл (все логи)
logger.add(
    "logs/bot.log",
    format=file_format,
    level="DEBUG",
    rotation="50 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].setdefault("user_id", "SYSTEM")
)

# 2. согласия 152-ФЗ (5 МБ лимит + автоотправка)
logger.add(
    "logs/agree_152fz.log",
    format=file_format,
    level="SUCCESS",  # используем SUCCESS для согласий
    rotation="5 MB",
    retention="90 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") == "agree" and record["extra"].setdefault("user_id", "SYSTEM"),
    serialize=False
)

# добавляем callback для автоотправки
logger.add(
    "logs/agree_152fz.log",
    format=file_format,
    level="SUCCESS",
    rotation=rotation_callback,  # callback при ротации
    retention="90 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") == "agree",
    serialize=False
)

# 3. действия юзеров (5 МБ + автоотправка)
logger.add(
    "logs/user_actions.log",
    format=file_format,
    level="INFO",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") == "user_action",
)

# 4. объявления (5 МБ + автоотправка)
logger.add(
    "logs/ads.log",
    format=file_format,
    level="INFO",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") in ("ad_action", "ad_view"),
)

# 5. модерация (5 МБ + автоотправка)
logger.add(
    "logs/moderation.log",
    format=file_format,
    level="INFO",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") == "moderation",
)

# 6. запросы контактов (5 МБ + автоотправка)
logger.add(
    "logs/contacts.log",
    format=file_format,
    level="INFO",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("log_type") == "contact",
)

# 7. ошибки
logger.add(
    "logs/error.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="WARNING",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True
)


# === УТИЛИТЫ ДЛЯ УДОБНОГО ЛОГИРОВАНИЯ ===

def log_user_action(user_id: int, username: str, action: str):
    """действие юзера"""
    logger.bind(user_id=f"user:{user_id}", log_type="user_action").info(
        f"@{username} (ID: {user_id}) {action}"
    )


def log_agree(user_id: int, username: str):
    """согласие 152-ФЗ"""
    logger.bind(user_id=f"user:{user_id}", log_type="agree").success(
        f"Пользователь @{username} ознакомился с Правилами использования сервиса и "
        f"Политикой конфиденциальности, дал свое согласие на обработку персональных данных"
    )


def log_ad_action(user_id: int, username: str, ad_id: int, action: str):
    """действия с объявлениями"""
    logger.bind(user_id=f"user:{user_id}", log_type="ad_action").info(
        f"@{username} (ID: {user_id}) {action} объявление #{ad_id}"
    )


def log_ad_view(user_id: int, username: str, ad_id: int, ad_title: str):
    """просмотр объявления"""
    logger.bind(user_id=f"user:{user_id}", log_type="ad_view").info(
        f"@{username} (ID: {user_id}) посмотрел объявление #{ad_id} '{ad_title}'"
    )


def log_moderation(moderator_id: int, moderator_username: str, ad_id: int, action: str, reason: str = ""):
    """модерация"""
    reason_text = f", причина: {reason}" if reason else ""
    logger.bind(user_id=f"user:{moderator_id}", log_type="moderation").info(
        f"Модератор @{moderator_username} (ID: {moderator_id}) {action} объявление #{ad_id}{reason_text}"
    )


def log_contact_request(buyer_id: int, buyer_username: str, seller_id: int, seller_username: str, ad_id: int, ad_title: str):
    """запрос контактов"""
    logger.bind(user_id=f"user:{buyer_id}", log_type="contact").info(
        f"@{buyer_username} (ID: {buyer_id}) запросил контакты продавца "
        f"@{seller_username} (ID: {seller_id}) по объявлению #{ad_id} '{ad_title}'"
    )


# === ДЕКОРАТОР ДЛЯ АВТОЛОГИРОВАНИЯ ===

def log_handler(log_type: str = "user_action"):
    """декоратор для автоматического логирования обработчиков"""
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            user_id = event.from_user.id if hasattr(event, 'from_user') else 0
            username = event.from_user.username if hasattr(event, 'from_user') else "unknown"
            
            logger.bind(user_id=f"user:{user_id}", log_type=log_type).debug(
                f"обработчик {func.__name__} вызван юзером @{username}"
            )
            
            return await func(event, *args, **kwargs)
        return wrapper
    return decorator


# === КРАСИВЫЙ ВЫВОД В ТЕРМИНАЛ ===

def setup_logging():
    """дополнительная настройка (если нужна)"""
    # настройка уровней для библиотек
    logger.disable("aiogram")
    logger.disable("asyncio")
    logger.disable("httpx")
    
    logger.info("🚀 система логирования запущена")


# вызываем при импорте
setup_logging()
