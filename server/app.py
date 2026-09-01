from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware


from src.api import router
from src.config import settings

# from src.bot.main import bot, dp, setup_bot, shutdown_bot
# from src.bot.webhook import router as webhook_router
# from src.bot.main import setup_bot, shutdown_bot


# from src.bot.setup import setup_bot_application
# from src.bot.application import application as bot_application
# from src.bot.endpoints import router as tg_router


from src.exception_handlers import add_exception_handlers
from src.health.endpoints import router as health_router
from src.kit.database.postgres import (
    AsyncEngine,
    AsyncSessionMaker,
    create_async_sessionmaker,
)
from src.kit.openapi import OPENAPI_PARAMETERS, APITag, set_openapi_generator
from src.logging import configure as configure_logging
from src.logging import get_logger
from src.middlewares import LogCorrelationIdMiddleware
from src.postgres import AsyncSessionMiddleware, create_async_engine
from src.scheduler import scheduler

# from src.subscriptions.scheduler_tasks import sync_remind_subscription_ends, sync_remove_subscription
# from src.deposit.scheduled_tasks import sync_check_cb_payment, sync_check_payment_interval, sync_check_sbp_payment, sync_check_stars_payment, sync_update_funds
import asyncio

log = get_logger()


class State(TypedDict):
    async_engine: AsyncEngine
    async_sessionmaker: AsyncSessionMaker


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:

    log.info("Starting Angar API")

    async_engine = create_async_engine("app")
    async_sessionmaker = create_async_sessionmaker(async_engine)

    # Initialize scheduler in thread pool
    scheduler.start()
    log.info("Scheduler started")

     # Initialize Telegram bot
    # try:
        # await setup_bot()
        # ONLY FOR WEBHOOK
    #     log.info("Telegram bot initialized")
    # except Exception as e:
    #     log.error("Error starting bot", exc_info=e)
    # try:
    #     await bot_application.initialize()
    #     log.info('Bot init')
    #     await bot_application.start()
    # except Exception as e:
    #     log.error("Error starting bot", exc_info=e)
    #     await bot_application.shutdown()


    # await setup_bot_application(bot_application)

    yield State(async_engine=async_engine, async_sessionmaker=async_sessionmaker)

    # Shutdown scheduler in thread pool
    scheduler.shutdown()
    log.info("API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        generate_unique_id_function=generate_unique_openapi_id,
        lifespan=lifespan,
        **OPENAPI_PARAMETERS,
    )

    if not settings.is_testing():
        app.add_middleware(AsyncSessionMiddleware)
    app.add_middleware(LogCorrelationIdMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173", 
            "http://localhost:3000", 
            "http://193.42.39.164:3000"
            "https://pbadev-app.gigabyteschatbots.ru"
        ], # Add your frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


    add_exception_handlers(app)

    # app.include_router(tg_router)
    app.include_router(router)
    app.include_router(health_router)

    return app


def generate_unique_openapi_id(route: APIRoute) -> str:
    parts = [str(tag) for tag in route.tags if tag not in APITag] + [route.name]
    return ":".join(parts)


configure_logging()

app = create_app()
set_openapi_generator(app)
