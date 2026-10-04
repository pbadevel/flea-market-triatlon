# src/services/sms/greensms_provider.py
import httpx

from src.services.sms.base import BaseSMSProvider
from src.exceptions import SMSDeliveryError
from src.logging import get_logger

logger = get_logger()


class GreenSMSProvider(BaseSMSProvider):
    """
    Провайдер GreenSMS API v3
    https://api3.greensms.ru/
    """

    BASE_URL = "https://api3.greensms.ru"

    def __init__(self, user: str, password: str, sender: str = "FleaMarket") -> None:
        self.user = user
        self.password = password
        self.sender = sender

    async def send(self, phone: str, message: str) -> str:
        """
        Отправка SMS через GreenSMS API
        
        Returns:
            request_id для отслеживания статуса
        """
        # Формат телефона для GreenSMS: без + (79991234567)
        phone_normalized = phone.lstrip("+")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/sms/send",
                    data={
                        "user": self.user,
                        "pass": self.password,
                        "to": phone_normalized,
                        "txt": message,
                        "from": self.sender,
                    },
                )

                data = response.json()

                # Успешная отправка
                if response.status_code == 200:
                    request_id = data.get("request_id")
                    logger.info(
                        "sms_sent_successfully",
                        phone=phone,
                        request_id=request_id,
                    )
                    return request_id

                # Обработка ошибок GreenSMS
                error_code = data.get("code", 0)
                error_message = data.get("error", "Unknown error")

                error_messages = {
                    0: "Ошибка авторизации. Проверьте credentials.",
                    -1: "Недостаточно средств на балансе.",
                    1: "Не указан обязательный параметр.",
                    2: "Неподдерживаемый тип параметра.",
                    3: "Неподдерживаемое значение параметра.",
                    4: "Аккаунт не активирован.",
                    6: "Превышен лимит для этого номера.",
                    8: "Слишком много запросов. Повторите через 60 секунд.",
                    9: "Внутренняя ошибка сервера.",
                    11: "Запрос ограничен.",
                }

                user_message = error_messages.get(error_code, f"Ошибка отправки SMS: {error_message}")
                logger.error(
                    "sms_send_failed",
                    phone=phone,
                    error_code=error_code,
                    error_message=error_message,
                    status_code=response.status_code,
                )
                raise SMSDeliveryError(user_message)

        except httpx.TimeoutException:
            logger.error("sms_send_timeout", phone=phone)
            raise SMSDeliveryError("Превышено время ожидания отправки SMS")
        except httpx.HTTPError as e:
            logger.error("sms_http_error", phone=phone, error=str(e))
            raise SMSDeliveryError(f"Ошибка сети при отправке SMS: {str(e)}")

    async def get_status(self, request_id: str) -> dict:
        """
        Проверка статуса доставки SMS
        
        Returns:
            dict с полями: status, status_code, time
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/sms/status",
                    params={
                        "user": self.user,
                        "pass": self.password,
                        "id": request_id,
                    },
                )

                if response.status_code == 200:
                    return response.json()

                data = response.json()
                logger.error(
                    "sms_status_check_failed",
                    request_id=request_id,
                    error=data.get("error"),
                )
                return {"status": "Unknown", "status_code": -1}

        except Exception as e:
            logger.error("sms_status_error", request_id=request_id, error=str(e))
            return {"status": "Error", "status_code": -1}