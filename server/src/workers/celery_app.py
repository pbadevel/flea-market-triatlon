"""Celery Application Configuration"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange


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
    
    # Критичные настройки для надёжности
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    
    task_default_queue="default",
    
    # Роутинг задач по очередям
    task_routes={
        "src.workers.tasks.send_notification_to_user": {
            "queue": "notifications",
            "routing_key": "notification",
        },
        "src.workers.tasks.broadcast_notification": {
            "queue": "broadcasts",
            "routing_key": "broadcast",
        },
        "src.workers.tasks.send_sms_task": {
            "queue": "sms",
            "routing_key": "sms",
        },
    },
    
    # Определение очередей с приоритетами
    task_queues=(
        Queue(
            "default",
            Exchange("tasks"),
            routing_key="default",
            queue_arguments={"x-max-priority": 10},
        ),
        Queue(
            "notifications",
            Exchange("notifications"),
            routing_key="notification",
            queue_arguments={"x-max-priority": 5},
        ),
        Queue(
            "broadcasts",
            Exchange("broadcasts"),
            routing_key="broadcast",
            queue_arguments={"x-max-priority": 1},
        ),
        Queue(
            "sms",
            Exchange("sms"),
            routing_key="sms",
            queue_arguments={"x-max-priority": 8},
        ),
    ),

    # Автоматический retry только для сетевых ошибок
    task_autoretry_for=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    task_retry_kwargs={"max_retries": 3, "countdown": 5},
    task_retry_backoff=True,
    task_retry_jitter=True,
)

# Rate limiting для разных типов задач
celery_app.conf.task_annotations = {
    "*": {"rate_limit": "10/s"},
    "src.workers.tasks.send_sms_task": {"rate_limit": "5/s"},
    "src.workers.tasks.broadcast_notification": {"rate_limit": "2/s"},
}

if __name__ == "__main__":
    celery_app.start()