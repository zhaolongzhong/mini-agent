import logging
from typing import Any, Dict, Optional, Protocol
from typing_extensions import runtime_checkable

import aiohttp
from httpx import HTTPError

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


class AioHTTPTransport(HTTPTransport):
    """AIOHTTP implementation of HTTP transport"""

    def __init__(self, base_url: str, session: Optional[aiohttp.ClientSession] = None):
        self.base_url = base_url
        self.is_server_available = False
        self.session = session or aiohttp.ClientSession(
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        if not self.is_server_available:
            return
        url = f"{self.base_url}{endpoint}"
        try:
            async with getattr(self.session, method.lower())(url, json=data, params=params) as response:
                if response.status >= 400:
                    error_data = await response.json()
                    logger.error(f"HTTP {response.status}: {error_data}")
                    raise HTTPError(f"HTTP {response.status}: {error_data.get('detail', 'Unknown error')}")
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}, url: {url}")
            raise ConnectionError(f"Request failed: {str(e)}")


class AioHTTPWebSocketTransport(WebSocketTransport):
    """AIOHTTP implementation of WebSocket transport"""

    def __init__(self, ws_url: str, client_id: str, session: Optional[aiohttp.ClientSession] = None):
        self.ws_url = ws_url
        self.session = session
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.client_id = client_id

    async def connect(self) -> None:
        if not self.ws or self.ws.closed:
            if "assistant" in self.client_id:
                user_id = "default_assistant_id"
            else:
                user_id = "default_user_id"
            ws_url_with_params = f"{self.ws_url}/{self.client_id}?user_id={user_id}"
            self.ws = await self.session.ws_connect(ws_url_with_params)
            logger.info(f"WebSocket connection established for client {self.client_id}")

    async def disconnect(self) -> None:
        if self.ws and not self.ws.closed:
            await self.ws.close()

    async def send(self, text: str) -> None:
        if not self.ws or self.ws.closed:
            await self.connect()
        await self.ws.send_str(text)

    async def receive(self) -> Dict[str, Any]:
        if not self.ws or self.ws.closed:
            await self.connect()
        return await self.ws.receive_json()


class ResourceClient:
    """Base class for resource-specific operations"""

    def __init__(self, http: HTTPTransport, ws: Optional[WebSocketTransport] = None):
        self._http = http
        self._ws = ws
