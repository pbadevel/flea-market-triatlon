from fastapi import APIRouter

from src.kit.database.service import database_service
from src.services.filters import get_filter_config

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("")
async def get_filters():
    async with database_service.get_session() as db:
        return await get_filter_config(db)