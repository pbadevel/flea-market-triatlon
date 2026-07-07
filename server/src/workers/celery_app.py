"""Celery Application Configuration"""
from celery import Celery

celery_app = Celery(
    "flea-market",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=280,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "src.workers.tasks.send_notification_to_user": {
            "queue": "notifications",
            "routing_key": "notification",
        },
        "src.workers.tasks.broadcast_notification": {
            "queue": "broadcasts",
            "routing_key": "broadcast",
        },
    },
    task_queues=None,
    task_autoretry_for=(ConnectionError, TimeoutError, OSError),
    task_retry_kwargs={"max_retries": 3, "countdown": 5},
    task_retry_backoff=True,
)

if __name__ == "__main__":
    celery_app.start()
