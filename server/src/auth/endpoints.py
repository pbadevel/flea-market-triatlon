from fastapi import Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.init_data import InitDataParser
from src.auth.init_data.verify import verify_init_data
from src.config import settings
from src.exceptions import Unauthorized
from src.kit.openapi import APITag
from src.postgres import get_db_session
from src.routing import APIRouter
from src.services.user import user_service

from .service import auth as auth_service

router = APIRouter(prefix="/test-miniapp-auth", tags=["Auth", APITag.documented])


@router.post("")
async def auth_telegram_miniapp(
    request: Request,
    init_data: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_db_session),
):
    if settings.is_production() and not verify_init_data(init_data):
        raise Unauthorized("Wrong init data hash")

    parsed_init_data = InitDataParser(init_data).parse()
    user = await user_service.get_or_create_by_init_data(
        session=session, init_data=parsed_init_data
    )
    return await auth_service.get_login_response(
        session=session, user=user, request=request
    )
