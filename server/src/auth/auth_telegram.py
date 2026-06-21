# src/api/endpoints/auth_telegram.py
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import secrets
import hashlib

from src.kit.database.service import database_service
from src.models import User, UserSession
from src.auth.service import auth as auth_service
from src.repositories.users import UserRepository
from src.kit.utils import utc_now

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthInitRequest(BaseModel):
    """Запрос на начало авторизации через Telegram"""
    pass


class TelegramAuthInitResponse(BaseModel):
    """Ответ с deeplink для бота"""
    deeplink: str
    session_token: str  # Временный токен для проверки статуса


class TelegramAuthCallbackRequest(BaseModel):
    """Callback от бота после подтверждения"""
    session_token: str
    tg_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramAuthStatusRequest(BaseModel):
    """Проверка статуса авторизации"""
    session_token: str


class TelegramAuthStatusResponse(BaseModel):
    status: str  # "pending", "completed", "expired"
    token: Optional[str] = None
    userId: Optional[str] = None
    role: Optional[str] = None


# Хранилище временных сессий авторизации (в продакшене лучше Redis)
_auth_sessions = {}


@router.post("/telegram/init", response_model=TelegramAuthInitResponse)
async def init_telegram_auth(request: Request):
    """
    Инициализация авторизации через Telegram.
    Если передан Authorization header — режим привязки (link).
    Если нет — режим входа (auth).
    """
    session_token = secrets.token_urlsafe(32)

    # Проверяем Authorization header для режима link
    auth_header = request.headers.get("Authorization", "")
    session_data = {
        "status": "pending",
        "created_at": utc_now(),
        "ip": request.client.host if request.client else None,
    }

    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        from src.auth.service import auth as auth_svc
        async with database_service.get_session() as db_session:
            user_session = await auth_svc.authenticate(db_session, token)
            if not user_session:
                raise HTTPException(401, detail="Неверный или истёкший токен")
            current_user = user_session.user
            if current_user.tg_user_id:
                raise HTTPException(400, detail="Telegram уже привязан к аккаунту")
            session_data["type"] = "link"
            session_data["user_id"] = current_user.id
    else:
        session_data["type"] = "auth"

    _auth_sessions[session_token] = session_data

    from src.config import settings
    bot_username = settings.BOT_USERNAME
    deeplink = f"https://t.me/{bot_username}?start=auth_{session_token}"

    return TelegramAuthInitResponse(
        deeplink=deeplink,
        session_token=session_token,
    )


@router.post("/telegram/callback")
async def telegram_auth_callback(data: TelegramAuthCallbackRequest, request: Request):
    """
    Callback от бота после подтверждения авторизации пользователем
    """
    # Проверяем существование сессии
    if data.session_token not in _auth_sessions:
        raise HTTPException(404, detail="Сессия авторизации не найдена или истекла")
    
    session_data = _auth_sessions[data.session_token]

    # Проверяем что сессия ещё активна (15 минут)
    from datetime import timedelta
    if utc_now() - session_data["created_at"] > timedelta(minutes=15):
        del _auth_sessions[data.session_token]
        raise HTTPException(410, detail="Сессия авторизации истекла")
    
    async with database_service.get_session() as session:
        repository = UserRepository(session)
        
        
        # Проверяем: это привязка или вход?
        is_link = session_data.get("type") == "link"
        
        if is_link:
            # Режим привязки — привязываем tg_user_id к существующему пользователю
            from src.models import User as UserModel
            existing_user = await repository.get_by_tg_id(data.tg_user_id)
            if existing_user:
                raise HTTPException(400, detail="Этот Telegram аккаунт уже привязан к другому пользователю")
            
            user = await repository.get_one_or_none(
                select(UserModel).where(UserModel.id == session_data["user_id"])
            )
            if not user:
                raise HTTPException(404, detail="Пользователь не найден")
            
            user.tg_user_id = data.tg_user_id
            if data.username:
                user.username = data.username
            if data.first_name:
                user.first_name = data.first_name
            if data.last_name:
                user.last_name = data.last_name
        else:
            # Режим входа — ищем или создаём пользователя
            user = await repository.get_by_tg_id(data.tg_user_id)
            
            if not user:
                # Создаём нового пользователя
                from src.models import User as UserModel
                user = await repository.create(
                    obj=UserModel(
                        tg_user_id=data.tg_user_id,
                        username=data.username,
                        first_name=data.first_name,
                        last_name=data.last_name,
                    ),
                    flush=True,
                )
            else:
                # Обновляем данные если изменились
                if data.username and user.username != data.username:
                    user.username = data.username
                if data.first_name and user.first_name != data.first_name:
                    user.first_name = data.first_name
                if data.last_name and user.last_name != data.last_name:
                    user.last_name = data.last_name
        
        # Создаём сессию для пользователя
        auth_response = await auth_service.get_login_response(
            session=session,
            user=user,
            request=request,  
            custom_user_agent=f"TG{data.tg_user_id}/0.1"
        )
        
        # Обновляем статус сессии
        _auth_sessions[data.session_token].update({
            "status": "completed",
            "token": auth_response.token,
            "user_id": str(user.id),
            "role": user.role.value if hasattr(user, 'role') else "user",
        })
        
        await session.commit()
        
        return {"status": "ok"}


@router.post("/telegram/status", response_model=TelegramAuthStatusResponse)
async def check_telegram_auth_status(data: TelegramAuthStatusRequest):
    """
    Проверка статуса авторизации (polling с клиента)
    """
    if data.session_token not in _auth_sessions:
        return TelegramAuthStatusResponse(status="expired")
    
    session_data = _auth_sessions[data.session_token]
    
    
    # Проверяем что сессия ещё активна
    from datetime import timedelta
    if utc_now() - session_data["created_at"] > timedelta(minutes=15):
        del _auth_sessions[data.session_token]
        return TelegramAuthStatusResponse(status="expired")
    
    if session_data["status"] == "completed":
        # Возвращаем данные авторизации
        response = TelegramAuthStatusResponse(
            status="completed",
            token=session_data["token"],
            userId=session_data["user_id"],
            role=session_data["role"],
        )
        print(session_data["token"])
        # Очищаем сессию после успешной проверки
        del _auth_sessions[data.session_token]
        return response
    
    return TelegramAuthStatusResponse(status="pending")