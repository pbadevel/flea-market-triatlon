import httpx

from src.services.sms.base import BaseSMSProvider
from src.exceptions import SMSDeliveryError
from src.logging import get_logger
from src.config import settings

logger = get_logger()


class GreenSMSProvider(BaseSMSProvider):
    """Провайдер GreenSMS API v3"""

    BASE_URL = "https://api3.greensms.ru"

    def __init__(self, user: str, password: str, sender: str = "GREENSMS") -> None:
        self.user = user
        self.password = password
        self.sender = sender
        # Используем CODE_PROVIDER из конфига
        self.code_provider = settings.CODE_PROVIDER  # "sms" или "telegram"

    async def send(self, phone: str, message: str) -> str:
        """Отправка кода через GreenSMS API"""
        phone_normalized = phone.replace("+", "")
        
        # Валидация для Telegram API
        if self.code_provider == "telegram":
            if not (4 <= len(message) <= 8):
                logger.error(f"message: {message}")
                raise SMSDeliveryError(
                    f"Telegram требует код 4-8 символов, получено {len(message)}"
                )
            if not message.isdigit():
                raise SMSDeliveryError("Telegram принимает только цифровые коды")

        logger.info(
            "sending_code",
            phone=phone_normalized,
            provider=self.code_provider,
            code_length=len(message),
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Базовые параметры
                payload = {
                    "user": self.user,
                    "pass": self.password,
                    "to": phone_normalized,
                    "txt": message,
                }

                # Для Telegram можно добавить cascade на SMS
                if self.code_provider == "telegram":
                    payload["cascade"] = "sms"  # Если Telegram не дойдёт, отправим SMS
                    payload["cascade_txt"] = message  # Тот же код
                    payload["ttl"] = 300  # 5 минут

                response = await client.post(
                    f"{self.BASE_URL}/{self.code_provider}/send",
                    data=payload,
                )

                data = response.json()

                # Успешная отправка
                if response.status_code == 200:
                    request_id = data.get("request_id")
                    logger.info(
                        "code_sent_successfully",
                        phone=phone_normalized,
                        request_id=request_id,
                        provider=self.code_provider,
                    )
                    return request_id

                # Обработка ошибок
                error_code = data.get("code", 0)
                error_message = data.get("error", "Unknown error")

                error_messages = {
                    0: "Ошибка авторизации GreenSMS",
                    -1: "Недостаточно средств",
                    1: f"Не указан параметр: {error_message}",
                    2: "Неподдерживаемый тип параметра",
                    3: "Неподдерживаемое значение параметра",
                    4: "Аккаунт не активирован",
                    6: "Превышен лимит для номера",
                    8: "Слишком много запросов",
                    9: "Внутренняя ошибка GreenSMS",
                    11: "Запрос ограничен",
                }

                user_message = error_messages.get(error_code, f"Ошибка: {error_message}")
                
                logger.error(
                    "code_send_failed",
                    phone=phone_normalized,
                    provider=self.code_provider,
                    error_code=error_code,
                    error_message=error_message,
                    status_code=response.status_code,
                )
                raise SMSDeliveryError(user_message)

        except httpx.TimeoutException:
            logger.error("code_send_timeout", phone=phone_normalized)
            raise SMSDeliveryError("Превышено время ожидания")
        except httpx.HTTPError as e:
            logger.error("code_http_error", phone=phone_normalized, error=str(e))
            raise SMSDeliveryError(f"Ошибка сети: {str(e)}")

    async def get_status(self, request_id: str) -> dict:
        """Проверка статуса доставки"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/{self.code_provider}/status",
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
                    "status_check_failed",
                    request_id=request_id,
                    error=data.get("error"),
                )
                return {"status": "Unknown", "status_code": -1}

        except Exception as e:
            logger.error("status_check_error", request_id=request_id, error=str(e))
            return {"status": "Error", "status_code": -1}