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

COUNTRY_MAP = {
    'russia': 'Россия',
    'россия': 'Россия',
    'ukraine': 'Украина',
    'украина': 'Украина',
    'belarus': 'Беларусь',
    'беларусь': 'Беларусь',
    'kazakhstan': 'Казахстан',
    'казахстан': 'Казахстан',
    'uzbekistan': 'Узбекистан',
    'узбекистан': 'Узбекистан',
    'georgia': 'Грузия',
    'грузия': 'Грузия',
    'armenia': 'Армения',
    'армения': 'Армения',
    'azerbaijan': 'Азербайджан',
    'азербайджан': 'Азербайджан',
    'turkey': 'Турция',
    'турция': 'Турция',
    'kyrgyzstan': 'Кыргызстан',
    'кыргызстан': 'Кыргызстан',
    'tajikistan': 'Таджикистан',
    'таджикистан': 'Таджикистан',
    'moldova': 'Молдова',
    'молдова': 'Молдова',
    'latvia': 'Латвия',
    'латвия': 'Латвия',
    'lithuania': 'Литва',
    'литва': 'Литва',
    'estonia': 'Эстония',
    'эстония': 'Эстония',
    'germany': 'Германия',
    'германия': 'Германия',
    'poland': 'Польша',
    'польша': 'Польша',
    'czech': 'Чехия',
    'чехия': 'Чехия',
    'usa': 'США',
    'united states': 'США',
    'china': 'Китай',
    'китай': 'Китай',
    'israel': 'Израиль',
    'израиль': 'Израиль',
}


def map_country(name: str | None) -> str | None:
    if not name:
        return None
    return COUNTRY_MAP.get(name.strip().lower(), name.capitalize())


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

