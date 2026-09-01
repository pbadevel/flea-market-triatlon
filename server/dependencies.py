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
    UserRepository
)


def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """Получить репозиторий пользователей"""
    return UserRepository(session)