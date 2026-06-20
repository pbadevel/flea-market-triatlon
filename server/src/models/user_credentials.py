# src/models/user_credentials.py
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    from .users import User


class UserCredentials(RecordModel):
    """
    Учётные данные для email-авторизации.
    Хранятся отдельно от User для безопасности и гибкости.
    """
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    # Хэш пароля (bcrypt)
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Токен для подтверждения email
    email_confirm_token: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # Подтверждён ли email
    is_email_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    # Связь с User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="credentials",
        lazy="joined",
    )