from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from src.kit.schemas import Schema
from pydantic import EmailStr, Field
from typing import Optional
import hashlib

from src.kit.database.service import database_service
from src.models import User, UserCredentials
from src.auth.service import auth as auth_service
from src.repositories import UserRepository, UserCredentialsRepository
from src.services.auth.password import hash_password, verify_password
from src.enums import UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class EmailRegisterRequest(Schema):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class EmailLoginRequest(Schema):
    email: EmailStr
    password: str


class AuthResponse(Schema):
    token: str
    success: bool
    userId: str
    role: str


@router.post("/register/email", response_model=AuthResponse)
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
        
        # Генерируем уникальный tg_user_id на основе email
        tg_user_id = int(hashlib.md5(data.email.encode()).hexdigest(), 16) % (10 ** 10)
        
        # Хэшируем пароль
        password_hash = hash_password(data.password)
        
        # Создаем пользователя
        user = await user_repository.create(
            obj=User(
                tg_user_id=tg_user_id,
                first_name=data.first_name,
                last_name=data.last_name,
                username=data.email,  # Используем email как username
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
        
        # Создаем сессию
        response = await auth_service.get_login_response(
            session=session,
            user=user,
            request=request,
        )
        
        await session.commit()
        
        return AuthResponse(
            token=response.token,
            success=True,
            userId=str(user.id),
            role=user.role.value,
        )


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