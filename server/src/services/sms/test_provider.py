# src/services/sms/test_provider.py
from src.logging import get_logger

from src.services.sms.base import BaseSMSProvider

logger = get_logger()


class TestSMSProvider(BaseSMSProvider):
    """Dev-провайдер: выводит SMS в лог, код виден в консоли."""

    async def send(self, phone: str, message: str) -> str:
        logger.warning("TEST_SMS_SENT", phone=phone, message=message)
        return "test-request-id"