from src.enums import UserRole
from src.kit.schemas import Schema


class ServerAuthResponse(Schema):
    token: str
    role: UserRole
    success: bool
    userId: str
