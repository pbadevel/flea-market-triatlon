
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.kit.database.models import RecordModel


class DeleteMessage(RecordModel):
    """Очередь на удаление сообщений."""
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[str] = mapped_column(String, nullable=False)