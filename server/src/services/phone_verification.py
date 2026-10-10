"""
Сервис верификации телефона через SMS-код с использованием GreenSMS API v3
"""
from __future__ import annotations

import hashlib
import re
import secrets

import redis.asyncio as redis
from src.logging import get_logger

from src.config import settings
from src.exceptions import PhoneVerificationError
from src.services.sms.factory import get_sms_provider

logger = get_logger()


def normalize_phone(phone: str) -> str:
    """Приводит номер к виду +79991234567"""
    digits = re.sub(r"\D", "", phone)

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "7" + digits

    if not (digits.startswith("7") and len(digits) == 11):
        raise PhoneVerificationError("Некорректный формат номера телефона")

    return f"+{digits}"


def _hash_code(code: str) -> str:
    """Хеш кода для безопасного хранения в Redis"""
    return hashlib.sha256(code.encode()).hexdigest()


class PhoneVerificationService:
    CODE_LENGTH_SMS = 6
    CODE_LENGTH_TELEGRAM = 6
    CODE_TTL = 300
    RESEND_COOLDOWN = 60
    MAX_ATTEMPTS = 5
    MAX_SENDS_PER_HOUR = 3

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client
        # Определяем длину кода в зависимости от провайдера
        code_provider = getattr(settings, 'CODE_PROVIDER', 'sms')
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'test')
        
        self.code_length = (
            self.CODE_LENGTH_TELEGRAM 
            if sms_provider == "greensms" and code_provider == "telegram"
            else self.CODE_LENGTH_SMS
        )
        
        logger.info(
            "phone_verification_service_init",
            sms_provider=sms_provider,
            code_provider=code_provider,
            code_length=self.code_length,
        )

    # ── ключи Redis ─────────────────────────────────────────────
    @staticmethod
    def _code_key(phone: str) -> str:
        return f"phone_verify:code:{phone}"

    @staticmethod
    def _attempts_key(phone: str) -> str:
        return f"phone_verify:attempts:{phone}"

    @staticmethod
    def _cooldown_key(phone: str) -> str:
        return f"phone_verify:cooldown:{phone}"

    @staticmethod
    def _hour_key(phone: str) -> str:
        return f"phone_verify:sends_hour:{phone}"

    @staticmethod
    def _request_id_key(phone: str) -> str:
        return f"phone_verify:request_id:{phone}"

    # ── отправка кода ───────────────────────────────────────────
    async def send_code(self, phone: str) -> tuple[str, str]:
        """
        Генерирует код, сохраняет в Redis и отправляет SMS
        
        Returns:
            (нормализованный номер, request_id)
        """
        phone = normalize_phone(phone)

        # Cooldown между отправками
        cooldown_ttl = await self._redis.ttl(self._cooldown_key(phone))
        if cooldown_ttl > 0:
            raise PhoneVerificationError(
                f"Код уже отправлен. Повторная отправка через {cooldown_ttl} сек."
            )

        # Лимит отправок в час
        hour_key = self._hour_key(phone)
        sends = await self._redis.incr(hour_key)
        if sends == 1:
            await self._redis.expire(hour_key, 3600)
        if sends > self.MAX_SENDS_PER_HOUR:
            raise PhoneVerificationError("Превышен лимит отправок. Попробуйте через час.")

        # Генерация кода с правильной длиной
        code = "".join(str(secrets.randbelow(10)) for _ in range(self.code_length))

        # Сохранение в Redis
        pipe = self._redis.pipeline()
        pipe.set(self._code_key(phone), _hash_code(code), ex=self.CODE_TTL)
        pipe.delete(self._attempts_key(phone))
        pipe.set(self._cooldown_key(phone), "1", ex=self.RESEND_COOLDOWN)
        await pipe.execute()

        # ИСПРАВЛЕНО: ТОЛЬКО КОД, БЕЗ ТЕКСТА!
        # Telegram API требует 4-8 символов, SMS тоже лучше короткий
        message = code

        logger.info(
            "generated_code",
            phone=phone,
            code_length=len(code),
            message_length=len(message),
        )

        # Отправка
        if settings.SMS_PROVIDER == "test":
            provider = get_sms_provider()
            request_id = await provider.send(phone, message)
        else:
            from src.workers.tasks import send_sms_task
            result = send_sms_task.delay(phone, message)
            request_id = result.id

        # Сохраняем request_id
        await self._redis.setex(
            self._request_id_key(phone),
            self.CODE_TTL,
            request_id,
        )

        logger.info(
            "verification_code_sent",
            phone=phone,
            request_id=request_id,
            code_length=self.code_length,
            message_length=len(message),
        )
        
        return phone, request_id

    # ── проверка кода ───────────────────────────────────────────
    async def verify_code(self, phone: str, code: str) -> str:
        """Проверяет код. При успехе очищает состояние."""
        phone = normalize_phone(phone)
        code_key = self._code_key(phone)

        stored_hash = await self._redis.get(code_key)
        if stored_hash is None:
            raise PhoneVerificationError("Код не найден или истёк. Запросите новый.")

        attempts_key = self._attempts_key(phone)
        attempts = await self._redis.incr(attempts_key)
        if attempts == 1:
            await self._redis.expire(attempts_key, self.CODE_TTL)

        if attempts > self.MAX_ATTEMPTS:
            await self._redis.delete(code_key, attempts_key)
            raise PhoneVerificationError("Превышено количество попыток. Запросите новый код.")

        if not secrets.compare_digest(stored_hash, _hash_code(code.strip())):
            left = self.MAX_ATTEMPTS - attempts
            raise PhoneVerificationError(f"Неверный код. Осталось попыток: {left}.")

        # Успех
        await self._redis.delete(
            code_key,
            attempts_key,
            self._cooldown_key(phone),
            self._request_id_key(phone),
        )
        logger.info("phone_code_verified", phone=phone)
        return phone

    # ── проверка статуса доставки SMS ───────────────────────────
    async def get_sms_status(self, phone: str) -> dict | None:
        """Проверяет статус доставки SMS через GreenSMS API"""
        phone = normalize_phone(phone)
        request_id = await self._redis.get(self._request_id_key(phone))
        
        if not request_id:
            return None

        if settings.SMS_PROVIDER != "greensms":
            return {"status": "Test mode", "status_code": 0}

        provider = get_sms_provider()
        return await provider.get_status(request_id)

    # ── статус для UI ───────────────────────────────────────────
    async def get_status(self, phone: str) -> dict:
        phone = normalize_phone(phone)
        code_ttl = await self._redis.ttl(self._code_key(phone))
        cooldown_ttl = await self._redis.ttl(self._cooldown_key(phone))
        attempts = await self._redis.get(self._attempts_key(phone))

        sms_status = await self.get_sms_status(phone)

        return {
            "active_code": code_ttl > 0,
            "code_ttl": max(code_ttl, 0),
            "resend_in": max(cooldown_ttl, 0),
            "attempts_left": self.MAX_ATTEMPTS - int(attempts or 0),
            "sms_status": sms_status,
        }