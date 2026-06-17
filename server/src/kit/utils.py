import uuid
import enum
from typing import TYPE_CHECKING

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
# from telegram.constants import ParseMode
# from telegram.ext import Defaults, ExtBot
from src.config import settings


# due circular import
class AdCondition(enum.StrEnum):
    new = "Новое"
    used = "Б/У"
    unknown = "Не указано"
    


if TYPE_CHECKING:
    from src.models import User

def utc_now() -> datetime:
    return datetime.now(UTC)

def get_ru_condition(condition_from_db: str):
    return AdCondition.__dict__[condition_from_db]

def get_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode='html')
    )


def generate_string_uuid() -> str:
    return str(uuid.uuid4())

