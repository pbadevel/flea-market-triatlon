from fastapi import APIRouter, HTTPException, Request, Query
from sqlalchemy import select
from src.kit.schemas import Schema
from pydantic import EmailStr, Field
from typing import Optional
import hashlib
import secrets

from src.kit.database.service import database_service
from src.kit.utils import utc_now
from src.models import User, UserCredentials
from src.auth.service import auth as auth_service
from src.repositories import UserRepository, UserCredentialsRepository
from src.services.auth.password import hash_password, verify_password
from src.services.email import email_service
from src.enums import UserRole
from src.config import settings
from src.logging import get_logger

log = get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


class EmailRegisterRequest(Schema):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = None


class EmailLoginRequest(Schema):
    email: EmailStr
    password: str


class AuthResponse(Schema):
    token: str
    success: bool
    userId: str
    role: str


@router.post("/register/email")
async def register_email(
    request: Request,
    data: EmailRegisterRequest,
):
    """
    Регистрация через email + password
    """
    async with database_service.get_session() as session:
        user_repository = UserRepository(session)
        user_creds_repository = UserCredentialsRepository(session)
        
        # Проверка существует ли пользователь с таким email в credentials
        stmt = select(UserCredentials).where(UserCredentials.email == data.email)
        result = await session.execute(stmt)
        existing_credentials = result.scalar_one_or_none()
        
        if existing_credentials:
            raise HTTPException(400, detail="Пользователь с таким email уже существует")

        # Хэшируем пароль
        password_hash = hash_password(data.password)
        
        # Создаем пользователя
        user = await user_repository.create(
            obj=User(
                tg_user_id=None,
                first_name=data.first_name,
                last_name=data.last_name,
                agreed_to_terms=True,
                role=UserRole.USER,
            ),
            flush=True,
        )
        
        # Создаем credentials
        user_creds = await user_creds_repository.create(
            obj=UserCredentials(
                user_id=user.id,
                email=data.email,
                password_hash=password_hash,
                is_email_verified=False,
            ),
            flush=True
        )
        
        # Генерируем токен подтверждения email
        confirm_token = secrets.token_urlsafe(32)
        user_creds.email_confirm_token = confirm_token
        await session.flush()
        
        await session.commit()
        
        # Отправляем письмо с подтверждением
        confirm_url = f"{settings.SITE_URL}/auth/confirm-email?token={confirm_token}"
        html = f"""<html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Добро пожаловать! 🎉</h2>
            <p>Вы зарегистрировались на flea-market.</p>
            <p>Подтвердите ваш email, перейдя по ссылке:</p>
            <p><a href=\"{confirm_url}\" style=\"display: inline-block; padding: 12px 24px; background: #2ecc71; color: white; text-decoration: none; border-radius: 8px;\">Подтвердить email</a></p>
            <p>Или скопируйте ссылку: {confirm_url}</p>
            <p style="margin-top: 20px; color: #888; font-size: 12px;">
                С уважением, команда flea-market
            </p>
        </body>
        </html>"""
        await email_service.send_email(
            to=data.email,
            subject="Подтверждение регистрации на flea-market",
            html_body=html,
        )
        
        return {"success": True, "message": "Письмо с подтверждением отправлено на email", "email": data.email}


@router.post("/resend-confirmation")
async def resend_confirmation(
    data: EmailRegisterRequest,
):
    """
    Повторная отправка письма с подтверждением email."""
    async with database_service.get_session() as session:
        # Ищем credentials по email
        stmt = select(UserCredentials).where(UserCredentials.email == data.email)
        result = await session.execute(stmt)
        creds = result.scalar_one_or_none()
        
        if not creds:
            raise HTTPException(404, detail="Пользователь с таким email не найден")
        
        if creds.is_email_verified:
            raise HTTPException(400, detail="Email уже подтверждён")
        
        # Генерируем новый токен
        creds.email_confirm_token = secrets.token_urlsafe(32)
        await session.flush()
        
        confirm_url = f"{settings.SITE_URL}/auth/confirm-email?token={creds.email_confirm_token}"
        html = f"""<html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Подтвердите email</h2>
            <p>Перейдите по ссылке для подтверждения регистрации:</p>
            <p><a href=\"{confirm_url}\" style="display: inline-block; padding: 12px 24px; background: #2ecc71; color: white; text-decoration: none; border-radius: 8px;">Подтвердить email</a></p>
            <p>Или скопируйте ссылку: {confirm_url}</p>
        </body>
        </html>"""
        
        await session.commit()
        
        await email_service.send_email(
            to=data.email,
            subject="Подтверждение email на flea-market",
            html_body=html,
        )
        
        return {"success": True, "message": "Письмо отправлено повторно"}


@router.get("/confirm-email", response_model=dict)
async def confirm_email(
    request: Request,
    token: str = Query(..., description="Токен подтверждения"),
):
    """
    Подтверждение email по токену + создание сессии.
    """
    async with database_service.get_session() as session:
        stmt = select(UserCredentials).where(
            UserCredentials.email_confirm_token == token,
            UserCredentials.is_email_verified == False,
        )
        result = await session.execute(stmt)
        creds = result.scalar_one_or_none()
        
        if not creds:
            return {"success": False, "message": "Неверный или устаревший токен"}
        
        # Подтверждаем email
        creds.is_email_verified = True
        creds.email_confirm_token = None
        await session.flush()
        
        # Создаём сессию для автоматического входа
        user = creds.user
        auth_response = await auth_service.get_login_response(
            session=session,
            user=user,
            request=request,
        )
        
        await session.commit()
        
        log.info("Email confirmed: %s (user %s)", creds.email, creds.user_id)
        
        return {
            "success": True,
            "message": "Email успешно подтверждён",
            "token": auth_response.token,
            "userId": str(user.id),
            "role": user.role
        }


@router.post("/login/email", response_model=AuthResponse)
async def login_email(
    request: Request,
    data: EmailLoginRequest,
):
    """
    Вход через email + password
    """
    async with database_service.get_session() as session:
        # Ищем credentials по email
        user_cred_repository = UserCredentialsRepository(session)

        credentials = await user_cred_repository.get_creds_by_email(data.email)

        if not credentials:
            raise HTTPException(401, detail="Неверный email или пароль")
        
        # Проверяем пароль
        if not verify_password(data.password, credentials.password_hash):
            raise HTTPException(401, detail="Неверный email или пароль")
        
        # Проверяем подтверждение email
        if not credentials.is_email_verified:
            raise HTTPException(403, detail="Email не подтверждён. Проверьте почту.")
        
        # Получаем пользователя
        user = credentials.user
        
        # Создаем сессию
        response = await auth_service.get_login_response(
            session=session,
            user=user,
            request=request,
        )
        
        return AuthResponse(
            token=response.token,
            success=True,
            userId=str(user.id),
            role=user.role.value,
        )