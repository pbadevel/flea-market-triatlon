# src/schemas/phone_verification.py
from pydantic import BaseModel, Field, field_validator

from src.services.phone_verification import normalize_phone


class SendCodeRequest(BaseModel):
    phone: str = Field(..., examples=["+79991234567"])

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


class VerifyCodeRequest(BaseModel):
    phone: str = Field(..., examples=["+79991234567"])
    code: str = Field(..., min_length=4, max_length=6, pattern=r"^\d+$", examples=["123456"])

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


class SendCodeResponse(BaseModel):
    success: bool = True
    phone: str
    request_id: str
    message: str = "Код отправлен на указанный номер"


class VerifyCodeResponse(BaseModel):
    success: bool = True
    phone: str
    message: str = "Номер телефона подтверждён"


class SMSStatusResponse(BaseModel):
    status: str | None = None
    status_code: int | None = None
    time: str | None = None


class PhoneStatusResponse(BaseModel):
    phone: str | None = None
    verified: bool = False
    active_code: bool = False
    code_ttl: int = 0
    resend_in: int = 0
    attempts_left: int = 5
    sms_status: SMSStatusResponse | None = None