"""Admin: notifications management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.auth.dependencies import WebAdmin
from src.workers.celery_app import celery_app

router = APIRouter(prefix="/notifications", tags=["admin-notifications"])


class SendNotificationRequest(BaseModel):
    user_id: int
    title: str
    message: str
    type: str = "info"


class BroadcastNotificationRequest(BaseModel):
    title: str
    message: str
    type: str = "info"


@router.post("/send")
async def send_notification(req: SendNotificationRequest, admin: WebAdmin):
    """Send notification to a specific user."""
    if not req.title.strip() or not req.message.strip():
        raise HTTPException(status_code=400, detail="Title and message are required")

    task = celery_app.send_task(
        "src.workers.tasks.send_notification_to_user",
        args=[req.user_id, req.title, req.message, req.type],
    )
    return {"status": "queued", "task_id": task.id}


@router.post("/broadcast")
async def broadcast_notification(req: BroadcastNotificationRequest, admin: WebAdmin):
    """Broadcast notification to all users."""
    if not req.title.strip() or not req.message.strip():
        raise HTTPException(status_code=400, detail="Title and message are required")

    task = celery_app.send_task(
        "src.workers.tasks.broadcast_notification",
        args=[req.title, req.message, req.type],
    )
    return {"status": "queued", "task_id": task.id}
