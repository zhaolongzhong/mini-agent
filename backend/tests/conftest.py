import os
import asyncio
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

base_url = os.environ.get("TEST_BASE_URL", "http://test")


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.
    Reference: https://github.com/pytest-dev/pytest-asyncio/discussions/587
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSessionLocal() as session:
            yield session
            await session.rollback()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


@pytest_asyncio.fixture
async def override_get_db(db: AsyncSession) -> AsyncGenerator[Callable, None]:
    async def _override_get_db():
        try:
            yield db
        except Exception as e:
            logger.error(f"Override get_db error: {e}")
            raise

    yield _override_get_db


@pytest_asyncio.fixture
async def main_app(override_get_db: Callable) -> AsyncGenerator[FastAPI, None]:
    app.dependency_overrides[deps.get_async_db] = override_get_db
    yield app
    app.dependency_overrides.clear()  # Clear overrides after test


@pytest_asyncio.fixture
async def async_client(main_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=main_app),
        base_url=base_url,
    ) as client:
        yield client
