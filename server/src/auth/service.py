from fastapi import Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import ServerAuthResponse
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

        return ServerAuthResponse(token=user_session.token, success=True, role=user.role, userId=str(user.id))

    async def _create_user_session(
        self, session: AsyncSession, user: User, user_agent: str = ""
    ) -> UserSession:
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user.id,
                UserSession.expires_at > utc_now(),
            )
        )
        res = await session.execute(stmt)
        old_session = res.unique().scalar_one_or_none()
        
        if old_session is None:
            user_session = UserSession(
                token=generate_token(), user_agent=user_agent, user=user
            )
            session.add(user_session)
            await session.flush()
            await session.commit()
    
        else:
            user_session = old_session

        return user_session


auth = AuthService()
