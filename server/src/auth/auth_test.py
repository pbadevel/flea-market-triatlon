# src/api/endpoints/auth_test.py
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.kit.database.service import database_service
from src.models import User
from src.enums import UserRole
from src.services.user import user_service
from src.auth.service import auth as auth_service

from pydantic import BaseModel
from fastapi import Request
from typing import Optional

router = APIRouter(prefix="/auth-test", tags=["auth-test"])

class TestLoginRequest(BaseModel):
    tg_user_id: int = 123456789  # Тестовый ID

@router.post("/login")
async def test_login(
    request: Request,
    data: Optional[TestLoginRequest] = None,
):
    """
    Тестовая авторизация без проверки init_data
    Использовать ТОЛЬКО для разработки!
    """
    tg_user_id = data.tg_user_id if data else 999999999
    
    async with database_service.get_session() as session:
        # Создаем или находим тестового пользователя
        from telegram import User as TGUser
        tg_user = TGUser(
            id=tg_user_id,
            first_name="Test",
            last_name="User",
            username="testuserrr",
            is_bot=False
        )
        
        user = await user_service.get_or_create_by_tg(session, tg_user)
        
        # Делаем его модератором для тестов
        user.role = UserRole.MODERATOR
        await session.commit()
        await session.flush()
        
        # Создаем сессиюF
        response = await auth_service.get_login_response(
            session=session,
            user=user,
            request=request,
        )
        
        await session.commit()
        
        return {
            "token": response.token,
            "userId": str(user.id),
            "role": user.role,
            "success": True,
        }