from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.scope import Scope
from src.enums import UserRole
from src.exceptions import Forbidden, Unauthorized
from src.models import User, UserSession
from src.postgres import get_db_session

from .service import auth as auth_service

user_session_scheme = HTTPBearer(
    scheme_name="user_session",
    auto_error=False,
    description="User session JWT token",
)


async def get_user_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(user_session_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> UserSession | None:
    if credentials is None:
        return None

    return await auth_service.authenticate(
        session=session, token=credentials.credentials
    )


def get_user(user_session: UserSession | None = Depends(get_user_session)) -> User:
    if user_session is None:
        raise Unauthorized(message="No user session")
    return user_session.user


class Authenticator:
    SCOPES_BY_ROLE = {
        UserRole.USER: {Scope.web_default},
        UserRole.CONTROLLER: {Scope.web_default},
        UserRole.ADMIN: {Scope.web_default, Scope.web_admin},
    }

    def __init__(self, scopes: set[Scope]):
        self.scopes = frozenset(scopes)

    def __call__(self, user: User = Depends(get_user)) -> User:
        if self.has_allowed_role(role=user.role) is False:
            raise Forbidden

        return user

    def has_allowed_role(self, role: UserRole) -> bool:
        role_scopes = self.SCOPES_BY_ROLE[role]

        for scope in self.scopes:
            if scope in role_scopes:
                return True

        return False


WebUserAuthenticator = Authenticator(scopes={Scope.web_default})
WebUser = Annotated[User, Depends(WebUserAuthenticator)]

WebAdminAuthenticator = Authenticator(scopes={Scope.web_admin})
WebAdmin = Annotated[User, Depends(WebAdminAuthenticator)]
