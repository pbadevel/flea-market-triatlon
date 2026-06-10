from typing import Optional, List
from fastapi import Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from src.kit.openapi import APITag
from src.auth.dependencies import WebUser, WebAdmin
from src.kit.pagination import ListResource, PaginationParamsQuery
from src.postgres import get_db_session
from src.routing import APIRouter
from src.exceptions import ValueRequestError
from src.scheduler import scheduler


from src.services.user import user_service

from src.logging import get_logger




log = get_logger()

router = APIRouter(
    prefix="/users",
    tags=["Users", APITag.private],
)


