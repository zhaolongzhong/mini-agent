import logging
from typing import Callable, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api import deps
from src.app.main import app
from src.app.database import AsyncSessionLocal
from src.app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture()
def override_get_db(db: AsyncSession) -> Callable:
    # Reference: https://rogulski.it/blog/sqlalchemy-14-async-orm-with-fastapi/
    async def _override_get_db():
        yield db

    return _override_get_db


@pytest.fixture()
def main_app(override_get_db: Callable) -> FastAPI:
    # from src.app.main import app

    app.dependency_overrides[deps.get_async_db] = override_get_db
    return app


@pytest.fixture()
async def async_client(main_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client:
        yield client
