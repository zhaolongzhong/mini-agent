import logging
from typing import Any

from sqlalchemy.orm import sessionmaker, as_declarative
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declared_attr

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    settings = get_settings()
    return settings.SQLALCHEMY_DATABASE_URI_ASYNC


db_url = get_database_url()

connect_args = {}

async_engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections every 30 minutes
    connect_args=connect_args,
)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@as_declarative()
class Base:
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
