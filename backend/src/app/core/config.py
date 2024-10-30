import sys
import secrets
from typing import Any, ClassVar
from functools import lru_cache

from pydantic import (
    HttpUrl,
    AnyHttpUrl,
    PostgresDsn,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SERVER_NAME: str
    SERVER_HOST: AnyHttpUrl
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080"]'
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8000/ws",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    SERVER_NAME: str | None = None
    SERVER_HOST: AnyHttpUrl | None = None
    PROJECT_NAME: str | None = None

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list | str):
            return v
        raise ValueError(v)

    SENTRY_DSN: HttpUrl | None = None

    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    SQLALCHEMY_DATABASE_URI_SYNC: str | None = None
    SQLALCHEMY_DATABASE_URI_ASYNC: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI_SYNC", mode="before")
    def assemble_db_connection_sync(cls, v: str | None, info: ValidationInfo) -> Any:
        assert info.data is not None
        values = info.data
        if isinstance(v, str):
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_HOST"),
                path=f"{values.get('POSTGRES_DB') or ''}",
                port=values.get("POSTGRES_PORT"),
            )
        )

    @field_validator("SQLALCHEMY_DATABASE_URI_ASYNC", mode="before")
    def assemble_db_connection_async(cls, v: str | None, info: ValidationInfo) -> Any:
        assert info.data is not None
        values = info.data
        if isinstance(v, str):
            return v

        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_HOST"),
                path=f"{values.get('POSTGRES_DB') or ''}",
                port=values.get("POSTGRES_PORT"),
            )
        )

    OPENAI_API_KEY: str
    ENVIRONMENT: str | None = "production"
    VERSION: str | None = "0.0.1"

    if "pytest" in sys.modules:
        env_file: ClassVar[str] = ".env.test"
    else:
        env_file: ClassVar[str] = ".env"

    model_config = SettingsConfigDict(
        env_file=env_file,
        env_file_encoding="utf-8",
        from_attributes=True,
        extra="ignore",
    )

    def __hash__(self):
        return hash(self.SECRET_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
