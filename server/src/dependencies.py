from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.scope import Scope
from src.enums import UserRole
from src.exceptions import Forbidden, Unauthorized
from src.models import User, UserSession
from src.postgres import get_db_session

from src.repositories import (
    UserRepository,
    ActionRepository,
    EventRepository,
    StudentCardRepository,
    CheckinRepository,
    MediaRepository
)


def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """Получить репозиторий пользователей"""
    return UserRepository(session)

def get_action_repo(session: AsyncSession = Depends(get_db_session)) -> ActionRepository:
    """Получить репозиторий акций"""
    return ActionRepository(session)

def get_event_repo(session: AsyncSession = Depends(get_db_session)) -> EventRepository:
    """Получить репозиторий мероприятий"""
    return EventRepository(session)

def get_student_card_repo(session: AsyncSession = Depends(get_db_session)) -> StudentCardRepository:
    """Получить репозиторий студ. карт"""
    return StudentCardRepository(session)

def get_checkin_repo(session: AsyncSession = Depends(get_db_session)) -> CheckinRepository:
    """Получить репозиторий проходок студентов"""
    return CheckinRepository(session)

def get_media_repo(session: AsyncSession = Depends(get_db_session)) -> MediaRepository:
    """Получить репозиторий медиа"""
    return MediaRepository(session)

