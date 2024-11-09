import logging
from typing import Annotated
from functools import lru_cache
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.config import Settings, get_settings
from app.embedding_manager import EmbeddingManager
from app.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@lru_cache
def get_embedding_manager_factory(api_key: str) -> EmbeddingManager:
    return EmbeddingManager(api_key=api_key)


def get_embedding_manager(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingManager:
    return get_embedding_manager_factory(settings.OPENAI_API_KEY)


SessionDep = Annotated[AsyncSession, Depends(get_async_db)]


@lru_cache
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()
