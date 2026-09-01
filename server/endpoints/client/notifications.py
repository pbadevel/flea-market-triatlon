"""Client: уведомления."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, update

from src.kit.database.service import database_service
from src.auth.dependencies import WebUser
from src.models import Notification
from src.enums import UserRole

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    ad_id: int | None = None
    created_at: str


@router.get("")
async def list_notifications(user: WebUser):
    async with database_service.get_session() as session:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        notifications = result.scalars().all()
        return [
            NotificationOut(
                id=n.id, title=n.title, message=n.message,
                type=n.type, is_read=n.is_read, ad_id=n.ad_id,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in notifications
        ]


@router.get("/unread-count")
async def unread_count(user: WebUser):
    async with database_service.get_session() as session:
        result = await session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        )
        count = result.scalar() or 0
        return {"count": count}


@router.post("/read-all")
async def mark_all_read(user: WebUser):
    async with database_service.get_session() as session:
        await session.execute(
            update(Notification)
            .where(Notification.user_id == user.id, Notification.is_read == False)
            .values(is_read=True)
        )
        await session.commit()
        return {"status": "ok"}
