# src/endpoints/client/phone_verification.py
from fastapi import APIRouter, Depends

from src.auth.dependencies import (
    get_user,
    get_phone_verification_service,
    get_user_repo,
)
from src.exceptions import PhoneVerificationError
from src.models.users import User
from src.repositories.users import UserRepository
from src.schemas.phone_verification import (
    PhoneStatusResponse,
    SendCodeRequest,
    SendCodeResponse,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from src.services.phone_verification import PhoneVerificationService

router = APIRouter(prefix="/phone-verification", tags=["phone-verification"])


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(
    payload: SendCodeRequest,
    user: User = Depends(get_user),
    service: PhoneVerificationService = Depends(get_phone_verification_service),
):
    """Отправка кода подтверждения на номер телефона"""
    phone, request_id = await service.send_code(payload.phone)
    return SendCodeResponse(phone=phone, request_id=request_id)


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(
    payload: VerifyCodeRequest,
    user: User = Depends(get_user),
    service: PhoneVerificationService = Depends(get_phone_verification_service),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Проверка кода и подтверждение номера"""
    phone = await service.verify_code(payload.phone, payload.code)
    phone = phone.replace("+", "")
    # Проверка уникальности номера
    existing = await user_repo.get_by_phone(phone)
    if existing and existing.id != user.id:
        raise PhoneVerificationError("Этот номер уже привязан к другому аккаунту")

    await user_repo.set_verified_phone(user.id, phone)
    return VerifyCodeResponse(phone=phone)


@router.get("/status", response_model=PhoneStatusResponse)
async def get_status(
    user: User = Depends(get_user),
    service: PhoneVerificationService = Depends(get_phone_verification_service),
):
    """Статус верификации для фронтенда"""
    if not user.phone:
        return PhoneStatusResponse()

    status = await service.get_status(user.phone)
    return PhoneStatusResponse(
        phone=user.phone,
        verified=user.phone_verified,
        **status,
    )