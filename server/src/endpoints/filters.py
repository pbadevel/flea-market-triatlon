from fastapi import APIRouter
from src.services.filters import get_filter_config

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("")
async def get_filters():
    return get_filter_config()