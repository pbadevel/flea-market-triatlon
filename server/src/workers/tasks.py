"""
Celery Tasks - асинхронные задачи

ВАЖНО: Celery tasks используют NullPool для предотвращения утечки соединений.
Каждая задача получает ровно одно соединение и освобождает его по завершении.
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, AsyncGenerator
from celery import Task

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.pool import NullPool

from src.workers.celery_app import celery_app
from src.services.sms import get_sms_provider
from src.config import settings
from src.exceptions import SMSDeliveryError

logger = get_task_logger(__name__)


@asynccontextmanager
async def get_celery_db_session() -> AsyncGenerator[tuple[AsyncSession, AsyncEngine], None]:
    """
    Context manager для получения DB session в Celery tasks.

    ВАЖНО: Использует NullPool - никакого кэширования соединений!
    Каждый вызов создаёт новое соединение, которое закрывается при выходе.
    Это критично для Celery workers, где много задач могут выполняться параллельно.

    Usage:
        async with get_celery_db_session() as (session, engine):
            # use session
            await session.commit()
        # engine.dispose() вызывается автоматически
    """
    engine = create_async_engine(
        settings.get_postgres_dsn("asyncpg"),
        echo=False,
        poolclass=NullPool,  # НЕТ пула - одно соединение на задачу
        connect_args={
            "server_settings": {
                "statement_timeout": "300000",  # 5 min max query time
                "idle_in_transaction_session_timeout": "900000",  # 15 min
            },
            "command_timeout": 300,
        },
    )

    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()
    try:
        yield session, engine
    finally:
        try:
            await session.close()
        except Exception as e:
            logger.warning(f"Error closing session: {e}")
        try:
            await engine.dispose()
        except Exception as e:
            logger.warning(f"Error disposing engine: {e}")


class DatabaseTask(Task):
    """Базовая задача с доступом к БД"""
    _db = None


def run_async(coro):
    """
    Запустить async функцию в sync контексте

    В Celery worker процессах всегда создаём новый event loop для каждой задачи,
    чтобы избежать "Event loop is closed" ошибки при повторных вызовах.

    Args:
        coro: Coroutine

    Returns:
        Результат выполнения
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(coro)
        return result
    finally:
        try:
            # Отменяем все pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            # Даём tasks время завершиться
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Закрываем все async generators
            loop.run_until_complete(loop.shutdown_asyncgens())

            # Закрываем loop
            loop.close()
        except Exception as e:
            logger.warning(f"Error during loop cleanup: {e}")


@celery_app.task(
    bind=True,
    name="src.workers.tasks.send_notification_to_user",
    acks_late=True,
    time_limit=60,
    soft_time_limit=50,
    max_retries=3,
    default_retry_delay=10,
)
def send_notification_to_user(
    self, user_id: int, title: str, message: str, notification_type: str = "info"
) -> Dict[str, Any]:
    """Send a single notification to a specific user."""

    async def _send():
        from src.models import Notification

        async with get_celery_db_session() as (session, engine):
            try:
                notification = Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    type=notification_type,
                    is_read=False,
                )
                session.add(notification)
                await session.commit()
                await session.refresh(notification)

                logger.info("Notification sent to user %d: %s", user_id, title)
                return {
                    "status": "ok",
                    "user_id": user_id,
                    "notification_id": notification.id,
                }
            except Exception as e:
                logger.error("Failed to send notification to user %d: %s", user_id, e)
                await session.rollback()
                raise

    try:
        return run_async(_send())
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))
        else:
            logger.error("Max retries reached for notification to user %d", user_id)
            return {"status": "failed", "user_id": user_id, "error": str(e)}


@celery_app.task(
    bind=True,
    name="src.workers.tasks.broadcast_notification",
    acks_late=True,
    time_limit=600,  # 10 минут для массовых рассылок
    soft_time_limit=540,
    max_retries=2,
    default_retry_delay=60,
)
def broadcast_notification(
    self, title: str, message: str, notification_type: str = "info"
) -> Dict[str, Any]:
    """Broadcast notification to all users in batches."""

    async def _broadcast():
        from sqlalchemy import select, func
        from src.models import Notification, User

        async with get_celery_db_session() as (session, engine):
            try:
                total_users = (
                    await session.execute(select(func.count(User.id)))
                ).scalar() or 0
                logger.info("Starting broadcast to %d users", total_users)

                batch_size = 500
                offset = 0
                created = 0

                while offset < total_users:
                    users = (
                        await session.execute(
                            select(User.id).offset(offset).limit(batch_size)
                        )
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
                    await session.commit()
                    created += len(users)
                    offset += batch_size
                    logger.info("Broadcast progress: %d/%d users", created, total_users)

                logger.info("Broadcast complete: %d notifications created", created)
                return {"status": "ok", "total": total_users, "created": created}
            except Exception as e:
                logger.error("Broadcast failed: %s", e)
                await session.rollback()
                raise

    try:
        return run_async(_broadcast())
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        else:
            logger.error("Broadcast failed permanently: %s", e)
            return {"status": "failed", "error": str(e)}


@celery_app.task(
    bind=True,
    name="src.workers.tasks.send_sms_task",
    acks_late=True,
    time_limit=60,
    soft_time_limit=50,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_sms_task(self, phone: str, message: str) -> Dict[str, Any]:
    """
    Отправка SMS через Celery воркер с использованием GreenSMS API v3
    
    Args:
        phone: Номер телефона в формате +79991234567
        message: Текст сообщения
        
    Returns:
        dict с request_id и статусом
    """

    async def _send():
        provider = get_sms_provider()
        request_id = await provider.send(phone, message)
        return request_id

    try:
        request_id = run_async(_send())
        logger.info(
            f"SMS sent successfully"
            f"phone={phone}"
            f"request_id={request_id}"
            f"attempt={self.request.retries + 1}"
        )
        return {
            "status": "ok",
            "phone": phone,
            "request_id": request_id,
        }
    except SMSDeliveryError as e:
        # Ошибка от GreenSMS (недостаточно средств, неверный номер и т.д.)
        # НЕ ретраим такие ошибки — они постоянные
        logger.error(
            "SMS delivery error (permanent)"
            f"phone={phone}"
            f"request_id={request_id}"
            f"attempt={self.request.retries + 1}"
            f"error={str(e)}"
        )
        return {
            "status": "failed",
            "phone": phone,
            "error": str(e),
            "retryable": False,
        }
    except (ConnectionError, TimeoutError, OSError) as e:
        # Сетевые ошибки — ретраим с экспоненциальной задержкой
        logger.warning(
            "SMS send failed (network error, will retry)"
            f"phone={phone}"
            f"request_id={request_id}"
            f"attempt={self.request.retries + 1}"
            f"error={str(e)}"
            f"max_retries={self.max_retries}"
        )
        raise
    except Exception as e:
        # Неизвестные ошибки — логируем, но не ретраим
        logger.error(
            "SMS send failed (unexpected error)"
            f"phone={phone}"
            f"error={str(e)}"
            f"attempt={self.request.retries + 1}",
            exc_info=True
        )
        return {
            "status": "failed",
            "phone": phone,
            "error": f"Unexpected error: {str(e)}",
            "retryable": False,
        }


@celery_app.task(
    bind=True,
    name="src.workers.tasks.check_sms_status",
    acks_late=True,
    time_limit=60,
    soft_time_limit=50,
    max_retries=2,
    default_retry_delay=60,
)
def check_sms_status(self, phone: str, request_id: str) -> Dict[str, Any]:
    """
    Проверка статуса доставки SMS через GreenSMS API
    
    Args:
        phone: Номер телефона
        request_id: ID запроса от send_sms_task
        
    Returns:
        dict со статусом доставки
    """

    async def _check():
        provider = get_sms_provider()
        if hasattr(provider, "get_status"):
            status = await provider.get_status(request_id)
            return status
        else:
            return {"status": "Status check not supported by provider"}

    try:
        status = run_async(_check())
        logger.info(
            "SMS status check"
            f"phone={phone}"
            f"request_id={request_id}"
            f"status={status}"
        )
        return {
            "status": "ok",
            "phone": phone,
            "request_id": request_id,
            "delivery_status": status,
        }
    except Exception as e:
        logger.warning(
            "SMS status check failed"
            f"phone={phone}"
            f"request_id={request_id}"
            f"error={str(e)}"
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        return {
            "status": "failed",
            "phone": phone,
            "request_id": request_id,
            "error": str(e),
        }