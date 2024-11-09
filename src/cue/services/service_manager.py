import json
import asyncio
import logging
from typing import Any, Callable, Optional, Awaitable

import aiohttp
from aiohttp import ClientResponseError, ClientConnectionError

from ..config import get_settings
from .transport import (
    AioHTTPTransport,
    AioHTTPWebSocketTransport,
)
from .memory_client import MemoryClient
from .message_client import MessageClient
from .assistant_client import AssistantClient
from .websocket_manager import WebSocketManager
from ..utils.id_generator import generate_id
from .conversation_client import ConversationClient
from ..schemas.event_message import EventMessage

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manager for coordinating service clients and handling WebSocket interactions."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        on_receive_user_message: Callable[[dict[str, any]], Awaitable[None]] = None,
    ):
        self.base_url = base_url
        self.client_id = generate_id(prefix="ws_")
        self.on_receive_user_message = on_receive_user_message
        self.is_server_available = False

        # Set up transports
        self._session = session
        self._http = AioHTTPTransport(self.base_url, self._session)
        self._ws = AioHTTPWebSocketTransport(self.base_url.replace("http", "ws") + "/ws", self.client_id, self._session)

        self._ws_manager = WebSocketManager(
            ws_transport=self._ws,
            message_handlers={
                "client_leave": self._handle_client_leave,
                "client_connect": self._handle_client_connect,
                "ping": self._handle_ping,
                "pong": self._handle_pong,
                "generic": self._handle_generic,
                "message": self._handle_message,
                "message_chunk": self._handle_message_chunk,
                "prompt": self._handle_prompt,
                "assistant": self._handle_assistant,
            },
        )

        # Initialize resource clients
        self.assistants = AssistantClient(self._http)
        self.memories = MemoryClient(self._http)
        self.conversations = ConversationClient(self._http)
        self.messages = MessageClient(self._http)

    @classmethod
    async def create(
        cls, base_url: Optional[str] = None, on_receive_user_message: Callable[[dict[str, any]], Awaitable[None]] = None
    ):
        settings = get_settings()
        base_url = base_url or settings.API_URL
        session = aiohttp.ClientSession()
        return cls(base_url, session, on_receive_user_message)

    async def close(self) -> None:
        """Close all connections"""
        await self._ws.disconnect()
        await self._ws_manager.disconnect()
        await self._session.close()

    async def connect(self) -> None:
        """Establish connection to the service"""

        try:
            self.is_server_available = await self._check_server_availability()
            self._http.is_server_available = self.is_server_available
            if not self.is_server_available:
                return
        except Exception as e:
            logger.error(f"Server availability check failed: {e}")
            return
        await self._ws_manager.connect()

    async def disconnect(self) -> None:
        """Close all connections"""
        await self._ws_manager.disconnect()
        await self._session.close()

    async def broadcast(self, message: str) -> None:
        if not self.is_server_available:
            return
        await self._ws_manager.send_message(message)

    async def _handle_client_leave(self, message: dict[str, Any]) -> None:
        logger.info("Client has left.")

    async def _handle_client_connect(self, message: dict[str, Any]) -> None:
        logger.info("Client has connected.")

    async def _handle_ping(self, message: dict[str, Any]) -> None:
        await self._ws_manager.send_message("pong")
        logger.debug("Responded to ping with pong.")

    async def _handle_pong(self, message: dict[str, Any]) -> None:
        logger.debug("Received pong.")

    async def _handle_generic(self, message: dict[str, Any]) -> None:
        logger.debug(f"Handling generic message: {message}")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        logger.debug(f"Handling message: {message}")

    async def _handle_message_chunk(self, message: dict[str, Any]) -> None:
        logger.debug(f"Handling message chunk: {message}")

    async def _handle_prompt(self, message: dict[str, Any]) -> None:
        logger.debug(f"Handling prompt: {message}")
        if self.on_receive_user_message:
            try:
                event = EventMessage(**message)
                await self.on_receive_user_message(event)
            except Exception as e:
                logger.error(f"Failed to parse EventMessage: {e}")

    async def _handle_assistant(self, message: dict[str, Any]) -> None:
        """Handle assistant-related messages."""
        logger.debug(f"Handling assistant message: {json.dumps(message, indent=4)}")

    async def _check_server_availability(self) -> bool:
        """Check if the server is running by performing an HTTP GET request to the health endpoint."""
        health_url = f"{self.base_url}/health"
        logger.debug(f"Performing health check at {health_url}")
        try:
            async with self._session.get(health_url, timeout=10) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Health check failed with status {response.status}: {text}")
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Health check failed: {text}",
                        headers=response.headers,
                    )
                data = await response.json()
                if data.get("status") != "ok":
                    logger.error(f"Health check returned unexpected status: {data}")
                    raise ValueError(f"Unexpected health check status: {data.get('status')}")
                logger.debug("Server is available based on health check.")
                return True
        except asyncio.TimeoutError:
            logger.error("Health check request timed out.")
            raise
        except ClientConnectionError as e:
            logger.warning(f"Failed to connect to server for health check: {e}")
            return False
        except ClientResponseError as e:
            logger.error(f"Server responded with an error during health check: {e}")
        except json.JSONDecodeError:
            logger.error("Health check response is not valid JSON.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            raise
