import json
import asyncio
import logging
import platform
from typing import Callable, Optional, Awaitable

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
from ..schemas.feature_flag import FeatureFlag
from ..schemas.event_message import EventMessage

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manager for coordinating service clients and handling WebSocket interactions."""

    def __init__(
        self,
        feature_flag: FeatureFlag,
        mode: str,
        base_url: str,
        session: aiohttp.ClientSession,
        on_message: Callable[[dict[str, any]], Awaitable[None]] = None,
    ):
        self.feature_flag = feature_flag
        self.mode = mode
        self.base_url = base_url
        client_id_prefix = "assistant" if self.mode in ["cli", "runner"] else "user"
        self.client_id = generate_id(prefix=f"ws_{client_id_prefix}_")
        self.on_message = on_message
        self.is_server_available = False
        if platform.system() != "Darwin" and "http://localhost" in self.base_url:
            self.base_url = self.base_url.replace("http://localhost", "http://host.docker.internal")
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
                "user": self._handle_message,
                "assistant": self._handle_message,
            },
        )

        # Initialize resource clients
        self.assistants = AssistantClient(self._http)
        self.memories = MemoryClient(self._http)
        self.conversations = ConversationClient(self._http)
        self.messages = MessageClient(self._http)

    @classmethod
    async def create(
        cls,
        feature_flag: Optional[FeatureFlag] = FeatureFlag(),
        mode: Optional[str] = "cli",
        base_url: Optional[str] = None,
        on_message: Callable[[dict[str, any]], Awaitable[None]] = None,
    ):
        settings = get_settings()
        base_url = base_url or settings.API_URL
        session = aiohttp.ClientSession()
        return cls(feature_flag, mode, base_url, session, on_message)

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

        if self.feature_flag.enable_storage:
            await self._create_default_assistant()

    async def disconnect(self) -> None:
        """Close all connections"""
        await self._ws_manager.disconnect()
        await self._session.close()

    async def broadcast(self, message: str) -> None:
        if not self.is_server_available:
            return
        await self._ws_manager.send_message(message)

    async def _handle_client_leave(self, message: EventMessage) -> None:
        logger.info(f"Client has left: {message.payload.client_id}")

    async def _handle_client_connect(self, message: EventMessage) -> None:
        logger.info(f"Client {message.payload.client_id} has connected")

    async def _handle_ping(self, message: EventMessage) -> None:
        logger.debug(f"Received ping message: {message}")

    async def _handle_pong(self, message: EventMessage) -> None:
        logger.debug(f"Received pong message: {message}.")

    async def _handle_generic(self, message: EventMessage) -> None:
        logger.debug(f"Handling generic message: {message}")

    async def _handle_message(self, message: EventMessage) -> None:
        if self.on_message:
            try:
                await self.on_message(message)
            except Exception as e:
                # Catch any other errors in on_message handling
                logger.error(f"Error in on_message handling: {e}. Message content: {message.model_dump_json(indent=4)}")

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

    async def _create_default_assistant(self):
        assistant_id = await self.assistants.create_default_assistant()
        self.memories.set_default_assistant_id(assistant_id)
        conversation_id = await self.conversations.create_default_conversation()
        self.messages.set_default_conversation_id(conversation_id)
