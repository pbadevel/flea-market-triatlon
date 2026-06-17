import os
from datetime import timedelta
from enum import StrEnum
from typing import Literal

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    testing = "testing"
    sandbox = "sandbox"
    production = "production"


env = Environment(os.getenv("ANGAR_ENV", Environment.development))
env_file = ".env.testing" if env == Environment.testing else ".env"


class Settings(BaseSettings):
    ENV: Environment = Environment.development
    LOG_LEVEL: str = "DEBUG"

    # User session
    USER_SESSION_TTL: timedelta = timedelta(days=31)
    API_DOMAIN_URL: str

    # Database
    POSTGRES_USER: str = "baraholka"
    POSTGRES_PWD: str = "baraholka"  # password
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "baraholka_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0

    DEPOSIT_STAR_USD_PRICE: float = 1.0

    # TOKENS
    
    # Bot
    BOT_TOKEN: str = "8125064359:AAFff50933y2CWPLmr4RvA-TQn_xAmCiMWs"   # @BarakholkaWebRobot
    TELEGRAM_CHANNEL_ID: int = -1002731869744 # t.me/testpba2
    MODERATORS_CHAT_ID: int = -1004447243084 # https://t.me/+wEuhlR88kbA3NTBk
    BOT_USERNAME: str = "BarakholkaWebRobot"
    SITE_URL: str = "http://localhost:3000"
    WEBHOOK_PATH: str = "ada"
    WEBHOOK_URL: str = "adad"
    webhook_secret_token: SecretStr | None = None
    SUPPORT_USERNAME: str = ""
    ADMIN_IDS: list[int] = [1060834219]
    DEVELOPER_IDS: list[int] = []

    @field_validator("ADMIN_IDS", "DEVELOPER_IDS", mode="before")
    @classmethod
    def _parse_int_list(cls, v: object) -> list[int]:
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return []

  

    # Application behaviours
    API_PAGINATION_MAX_LIMIT: int = 100

    default_timezone: str = "Europe/Moscow"

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
    )

    
    def get_webhook_secret_token(self) -> str | None:
        if self.webhook_secret_token:
            return self.webhook_secret_token.get_secret_value()
        return None
    

    def get_postgres_dsn(self, driver: Literal["asyncpg", "psycopg2"]) -> str:
        return str(
            PostgresDsn.build(
                scheme=f"postgresql+{driver}",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PWD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DATABASE,
            )
        )

    def is_development(self) -> bool:
        return self.is_environment({Environment.development})

    def is_testing(self) -> bool:
        return self.is_environment({Environment.testing})

    def is_production(self) -> bool:
        return self.is_environment({Environment.production})

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments


settings = Settings()  # pyright: ignore
