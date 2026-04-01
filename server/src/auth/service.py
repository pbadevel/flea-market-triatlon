from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import MiniAppAuthResponse
from src.kit.crypto import generate_token
from src.kit.utils import utc_now
from src.logging import get_logger
from src.models import User, UserSession

log = get_logger()


class AuthService:
    async def authenticate(
        self, session: AsyncSession, token: str
    ) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.token == token, UserSession.expires_at > utc_now()
        )
        result = await session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_login_response(
        self, session: AsyncSession, user: User, request: Request
    ):
        user_session = await self._create_user_session(
            session=session, user=user, user_agent=request.headers.get("User-Agent", "")
        )

        return MiniAppAuthResponse(token=user_session.token, success=True, userId=str(user.id), role=user.role)

    async def _create_user_session(
        self, session: AsyncSession, user: User, user_agent: str = ""
    ) -> UserSession:
        user_session = UserSession(
            token=generate_token(), user_agent=user_agent, user=user
        )
        session.add(user_session)

        return user_session


auth = AuthService()
