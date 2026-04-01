from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.logging import get_logger

log = get_logger()

# jobstores = {
#     'default': SQLAlchemyJobStore(
#         url=settings.get_postgres_dsn("asyncpg").replace("+asyncpg", '')
#     )
# }

jobstores = {
    'default': SQLAlchemyJobStore(
        url=settings.get_postgres_dsn("asyncpg").replace("+asyncpg", ''),
        # engine_options={
        #     'pool_size': 5,
        #     'max_overflow': 10,
        #     'pool_recycle': 3600,
        # }
    )
}


executors = {
    'default': ThreadPoolExecutor(max_workers=20),
    'processpool': ProcessPoolExecutor(max_workers=5)
}

# Job defaults can also be configured
job_defaults = {
    'coalesce': True,  # Combine multiple pending executions
    'max_instances': 3,  # Maximum instances of a job that can run concurrently
    'misfire_grace_time': 60  # Seconds to wait for job to run if it missed its scheduled time
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
)


# scheduler = BackgroundScheduler(jobstores=jobstores)