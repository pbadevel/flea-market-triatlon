import uuid
from typing import TYPE_CHECKING

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram.constants import ParseMode
from telegram.ext import Defaults, ExtBot
from src.config import settings



if TYPE_CHECKING:
    from src.models import User

def utc_now() -> datetime:
    return datetime.now(UTC)

def get_bot() -> ExtBot:
    return ExtBot(
        token=settings.BOT_TOKEN.get_secret_value(),
        defaults=Defaults(parse_mode=ParseMode.HTML),
    )


def generate_string_uuid() -> str:
    return str(uuid.uuid4())


def with_user_timezone(dt: datetime, user: "User") -> datetime:
    return dt.replace(tzinfo=ZoneInfo(user.timezone))

def to_user_timezone(dt: datetime, user: "User") -> datetime:
    return dt.astimezone(ZoneInfo(user.timezone))

def get_plus_30_days_date() -> datetime:
    return utc_now() + timedelta(days=30)


def get_plus_3x30_days_date() -> datetime:
    return utc_now() + timedelta(days=3*30)

def get_plus_6x30_days_date() -> datetime:
    return utc_now() + timedelta(days=6*30)

def get_plus_12x30_days_date() -> datetime:
    return utc_now() + timedelta(days=12*30)

def get_plus_3_days_date() -> datetime:
    return utc_now() + timedelta(days=3)