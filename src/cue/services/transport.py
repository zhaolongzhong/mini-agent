import asyncio
import logging
from typing import Any, Dict, Optional, Protocol
from typing_extensions import runtime_checkable

import aiohttp
from httpx import HTTPError
from aiohttp.client_ws import ClientWSTimeout

logger = logging.getLogger(__name__)


@runtime_checkable
class HTTPTransport(Protocol):
    """Protocol for HTTP transport operations"""

    async def request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None
    ) -> Any: ...


@runtime_checkable
class WebSocketTransport(Protocol):
    """Protocol for WebSocket transport operations"""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def send(self, message: Dict[str, Any]) -> None: ...
    async def receive(self) -> Dict[str, Any]: ...


class ResourceClient:
    """Base class for resource-specific operations"""

    def __init__(self, http: HTTPTransport, ws: Optional[WebSocketTransport] = None):
        self._http = http
        self._ws = ws


class AioHTTPTransport(HTTPTransport):
    """AIOHTTP implementation of HTTP transport"""

    def __init__(self, base_url: str, access_token: str, session: Optional[aiohttp.ClientSession] = None):
        self.base_url = base_url
        self.access_token = access_token
        self.is_server_available = False
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        self.session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        if not self.is_server_available:
            return
        url = f"{self.base_url}{endpoint}"
        try:
            async with getattr(self.session, method.lower())(
                url, json=data, params=params, headers=self.headers
            ) as response:
                if response.status >= 400:
                    error_data = await response.json()
                    logger.error(f"HTTP {response.status}: {error_data}")
                    raise HTTPError(f"HTTP {response.status}: {error_data.get('detail', 'Unknown error')}")
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}, url: {url}")
            raise ConnectionError(f"Request failed: {str(e)}")


class WebSocketConnectionError(Exception):
    """Custom exception for WebSocket connection errors"""

    pass


class AioHTTPWebSocketTransport(WebSocketTransport):
    """Enhanced AIOHTTP implementation of WebSocket transport with retry logic and better error handling"""

    def __init__(
        self,
        ws_url: str,
        client_id: str,
        access_token: str,
        runner_id: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.ws_url = ws_url
        self.session = session or aiohttp.ClientSession()
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.client_id = client_id
        self.access_token = access_token
        self.runner_id = runner_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic and proper error handling"""
        if self._connected and self.ws and not self.ws.closed:
            return

        for attempt in range(self.max_retries):
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Connection": "upgrade",
                    "Upgrade": "websocket",
                    "Sec-WebSocket-Version": "13",
                }

                ws_url_with_params = f"{self.ws_url}/{self.client_id}"
                if self.runner_id:
                    ws_url_with_params += f"?runner_id={self.runner_id}"
                logger.debug(
                    f"Attempting WebSocket connection to {ws_url_with_params} (attempt {attempt + 1}/{self.max_retries})"
                )

                self.ws = await self.session.ws_connect(
                    ws_url_with_params, headers=headers, heartbeat=30.0, timeout=ClientWSTimeout(ws_close=30.0)
                )

                self._connected = True
                logger.info(f"WebSocket connection established for client {self.client_id}")
                return

            except aiohttp.ClientResponseError as e:
                if e.status == 401:
                    logger.error("Authentication failed: Invalid or expired access token")
                    raise WebSocketConnectionError("Authentication failed: Please check your access token")
                logger.error(f"HTTP error during WebSocket connection: {e.status} - {e.message}")

            except aiohttp.WSServerHandshakeError as e:
                logger.error(f"WebSocket handshake failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise WebSocketConnectionError(f"WebSocket handshake failed after {self.max_retries} attempts")

            except aiohttp.ClientError as e:
                logger.error(f"Connection error: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise WebSocketConnectionError(f"Failed to establish WebSocket connection: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error during WebSocket connection: {str(e)}")
                raise WebSocketConnectionError(f"Unexpected error: {str(e)}")

            await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def disconnect(self) -> None:
        """Safely close the WebSocket connection"""
        if self.ws and not self.ws.closed:
            try:
                await self.ws.close()
                self._connected = False
                logger.info(f"WebSocket connection closed for client {self.client_id}")
            except Exception as e:
                logger.error(f"Error during WebSocket disconnection: {str(e)}")

    async def send(self, text: str) -> None:
        """Send message with connection check and error handling"""
        try:
            if not self._connected or not self.ws or self.ws.closed:
                await self.connect()
            await self.ws.send_str(text)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise WebSocketConnectionError(f"Failed to send message: {str(e)}")

    async def receive(self) -> Dict[str, Any]:
        """Receive message with connection check and error handling"""
        try:
            if not self._connected or not self.ws or self.ws.closed:
                await self.connect()
            return await self.ws.receive_json()
        except Exception as e:
            logger.error(f"Error receiving message: {str(e)}")
            raise WebSocketConnectionError(f"Failed to receive message: {str(e)}")
