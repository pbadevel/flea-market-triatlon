from functools import lru_cache

from src.config import settings
from src.services.sms.base import BaseSMSProvider
from src.services.sms.greensms_provider import GreenSMSProvider
from src.services.sms.test_provider import TestSMSProvider


@lru_cache
def get_sms_provider() -> BaseSMSProvider:
    if settings.SMS_PROVIDER == "greensms":
        if not settings.greensms_user or not settings.greensms_password:
            raise RuntimeError("GREENSMS_USER и GREENSMS_PASSWORD должны быть заданы в .env")
        return GreenSMSProvider(
            user=settings.greensms_user,
            password=settings.greensms_password,
            sender=settings.SMS_SENDER,
        )
    return TestSMSProvider()