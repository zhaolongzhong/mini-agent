import logging
from typing import Optional, Annotated
from datetime import datetime, timezone
from functools import lru_cache
from collections.abc import AsyncGenerator

from jose import JWTError, jwt
from fastapi import Depends, WebSocket, HTTPException
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.config import Settings, get_settings
from app.core.security import ALGORITHM
from app.embedding_manager import EmbeddingManager
from app.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    user_id: str
    assistant_id: Optional[str] = None
    exp: datetime


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
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        return None


async def get_token_from_websocket(websocket: WebSocket) -> Optional[str]:
    """Extract token from WebSocket headers or query parameters"""
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return websocket.query_params.get("token")


async def get_current_user_and_assistant(
    websocket: WebSocket,
    settings: Settings,
) -> tuple[str, Optional[str]]:
    """
    Get current user ID and assistant ID from WebSocket token

    Returns:
        Tuple of (user_id, assistant_id)
    """
    token = await get_token_from_websocket(websocket)
    if not token:
        return None, None

    token_data = await validate_token(token, settings)
    return token_data.user_id, token_data.assistant_id


async def validate_token(
    token: str,
    settings: Settings,
) -> TokenData:
    """
    Validate the token and extract user_id and assistant_id

    Returns:
        TokenData object containing user_id and assistant_id
    Raises:
        HTTPException if token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        return TokenData(
            user_id=user_id,
            assistant_id=payload.get("aid"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
