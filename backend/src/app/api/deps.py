import logging
from typing import Optional, Annotated
from functools import lru_cache
from collections.abc import AsyncGenerator

from jose import JWTError, jwt
from fastapi import Depends, WebSocket, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    return token


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
) -> str:
    try:
        # Decode the JWT token
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        return None


async def authenticate_websocket_user(
    websocket: WebSocket,
    settings: Settings,
) -> Optional[str]:
    """Authenticate WebSocket connection using JWT token.

    Returns:
        str | None: User ID if authenticated, None if no token provided
    """
    token = await get_token_from_websocket(websocket)
    if not token:
        return None

    return await validate_token(token, settings)


async def get_token_from_websocket(websocket: WebSocket) -> Optional[str]:
    """Extract JWT token from WebSocket headers or query parameters.

    Returns:
        str | None: Bearer token if found, None otherwise
    """
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return websocket.query_params.get("token")


async def validate_token(
    token: str,
    settings: Settings,
) -> str:
    """Validate JWT token and extract user ID.

    Returns:
        str: Authenticated user ID
    Raises:
        HTTPException: If token is invalid or missing user ID
    """

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        return user_id

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
