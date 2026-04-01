from src.enums import UserRole
from src.kit.schemas import Schema


class MiniAppAuthResponse(Schema):
    token: str
    success: bool
    userId: str
    role: UserRole = UserRole.USER
