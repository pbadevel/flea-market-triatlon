"""Celery Tasks for notifications"""
import asyncio
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from src.workers.celery_app import celery_app
from src.models import Notification, User
from src.config import settings

logger = get_task_logger(__name__)

DATABASE_URL = settings.get_postgres_dsn(driver="psycopg2")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(bind=True, name="src.workers.tasks.send_notification_to_user")
def send_notification_to_user(self, user_id: int, title: str, message: str, notification_type: str = "info"):
    """Send a single notification to a specific user."""
    try:
        with SessionLocal() as session:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                is_read=False,
            )
            session.add(notification)
            session.commit()
            logger.info("Notification sent to user %d: %s", user_id, title)
            return {"status": "ok", "user_id": user_id}
    except Exception as e:
        logger.error("Failed to send notification to user %d: %s", user_id, e)
        raise self.retry(exc=e)


@celery_app.task(bind=True, name="src.workers.tasks.broadcast_notification")
def broadcast_notification(self, title: str, message: str, notification_type: str = "info"):
    """Broadcast notification to all users in batches."""
    try:
        with SessionLocal() as session:
            total_users = session.execute(select(func.count(User.id))).scalar() or 0
            logger.info("Starting broadcast to %d users", total_users)

            batch_size = 500
            offset = 0
            created = 0

            while offset < total_users:
                users = session.execute(
                    select(User.id).offset(offset).limit(batch_size)
                ).scalars().all()

                if not users:
                    break

                notifications = [
                    Notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        type=notification_type,
                        is_read=False,
                    )
                    for user_id in users
                ]
                session.add_all(notifications)
                session.commit()
                created += len(users)
                offset += batch_size
                logger.info("Broadcast progress: %d/%d users", created, total_users)

            logger.info("Broadcast complete: %d notifications created", created)
            return {"status": "ok", "total": total_users, "created": created}
    except Exception as e:
        logger.error("Broadcast failed: %s", e)
        raise self.retry(exc=e)
