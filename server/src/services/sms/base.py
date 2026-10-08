# src/services/sms/base.py
from abc import ABC, abstractmethod


class BaseSMSProvider(ABC):
    """Единый интерфейс SMS-провайдера."""

    @abstractmethod
    async def send(self, phone: str, message: str) -> str:
        """Отправить SMS. Возвращает request_id."""
        ...