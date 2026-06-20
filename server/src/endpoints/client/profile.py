# src/api/endpoints/profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.kit.database.service import database_service
from src.auth.dependencies import WebUser
from src.models import User, Ad, AdStatus, UserCredentials
from src.schemas.profile import UserProfileOut, UserProfileUpdate, UserStats
from src.repositories.users import UserRepository
from src.services.auth.password import hash_password
from src.services.email import email_service
import secrets
from src.enums import UserRole
from src.config import settings

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileOut)
async def get_my_profile(user: WebUser):
    """Получить данные текущего пользователя"""
    async with database_service.get_session() as session:
        # Получаем email из credentials
        stmt = select(UserCredentials).where(UserCredentials.user_id == user.id)
        result = await session.execute(stmt)
        credentials = result.scalar_one_or_none()
        
        # Возвращаем профиль с email
        profile_data = {
            "id": user.id,
            "tg_user_id": user.tg_user_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "email": credentials.email if credentials else None,
            "is_email_verified": credentials.is_email_verified if credentials else False,
            "is_moderator": user.role==UserRole.MODERATOR,
            "is_trusted_seller": user.is_trusted_seller,
            "agreed_to_terms": user.agreed_to_terms,
            "subscribed_to_channel": user.subscribed_to_channel,
            "created_at": user.created_at,
        }
        
        return UserProfileOut(**profile_data)


@router.patch("/me", response_model=UserProfileOut)
async def update_my_profile(
    data: UserProfileUpdate,
    user: WebUser,
):
    """Обновить данные текущего пользователя"""
    async with database_service.get_session() as session:
        repository = UserRepository(session)
        
        # ИСПРАВЛЕНО: Получаем свежий объект user в текущей сессии
        fresh_user = await repository.get_by_id(user.id)
        if not fresh_user:
            raise HTTPException(404, detail="Пользователь не найден")
        
        # Обновляем данные пользователя
        update_data = {}
        if data.first_name is not None:
            update_data["first_name"] = data.first_name
        if data.last_name is not None:
            update_data["last_name"] = data.last_name
        if data.phone is not None:
            update_data["phone"] = data.phone
        
        if update_data:
            await repository.update(
                obj=fresh_user,
                update_dict=update_data,
                flush=True,
            )
        
        # Обновляем email в credentials если нужно
        if data.email is not None:
            stmt = select(UserCredentials).where(UserCredentials.user_id == fresh_user.id)
            result = await session.execute(stmt)
            credentials = result.scalar_one_or_none()
            
            if credentials:
                email_changed = credentials.email != data.email
                if email_changed:
                    credentials.email = data.email
                    credentials.is_email_verified = False
                    credentials.email_confirm_token = secrets.token_urlsafe(32)
                    await session.flush()
                    
                    if data.email:
                        confirm_url = f"{settings.SITE_URL}/auth/confirm-email?token={credentials.email_confirm_token}"
                        html = f"""<html><body style="font-family:Arial;padding:20px">
                            <h2>Подтвердите email</h2>
                            <p>Перейдите по ссылке:</p>
                            <p><a href=\"{confirm_url}\" style="display:inline-block;padding:12px 24px;background:#2ecc71;color:white;text-decoration:none;border-radius:8px">Подтвердить</a></p>
                        </body></html>"""
                        await email_service.send_email(to=data.email, subject="Подтверждение email", html_body=html)
            else:
                new_creds = UserCredentials(
                    user_id=fresh_user.id,
                    email=data.email,
                    password_hash=hash_password(secrets.token_urlsafe(32)),
                    is_email_verified=False,
                )
                session.add(new_creds)
                await session.flush()
                
                if data.email:
                    confirm_url = f"{settings.SITE_URL}/auth/confirm-email?token={credentials.email_confirm_token}"
                    html = f"""<html><body style="font-family:Arial;padding:20px">
                        <h2>Подтвердите регистрацию</h2>
                        <p><a href=\"{confirm_url}\" style="display:inline-block;padding:12px 24px;background:#2ecc71;color:white;text-decoration:none;border-radius:8px">Подтвердить email</a></p>
                    </body></html>"""
                    await email_service.send_email(to=data.email, subject="Подтверждение регистрации", html_body=html)
        
        await session.commit()
        
        # Возвращаем обновленный профиль
        return await get_my_profile(fresh_user)


@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(user: WebUser):
    """Получить статистику объявлений пользователя"""
    async with database_service.get_session() as session:
        # Считаем объявления по статусам
        stmt = select(Ad.status, func.count(Ad.id)).where(
            Ad.seller_user_id == user.id
        ).group_by(Ad.status)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # ИСПРАВЛЕНО: правильно конвертируем в dict
        stats_dict = {row[0]: row[1] for row in rows}
        
        total_ads = sum(stats_dict.values())
        
        return UserStats(
            total_ads=total_ads,
            active_ads=stats_dict.get(AdStatus.approved.value, 0),
            pending_ads=stats_dict.get(AdStatus.pending.value, 0),
            approved_ads=stats_dict.get(AdStatus.approved.value, 0),
            rejected_ads=stats_dict.get(AdStatus.rejected.value, 0),
            sold_ads=stats_dict.get(AdStatus.sold.value, 0),
        )