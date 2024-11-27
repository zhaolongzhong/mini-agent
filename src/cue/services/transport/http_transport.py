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
            logger.error("Server is not available.")
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
