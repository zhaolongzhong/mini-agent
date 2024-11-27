from typing import Optional

from .http_transport import HTTPTransport
from .websocket_transport import WebSocketTransport


class ResourceClient:
    """Base class for resource-specific operations"""

    def __init__(self, http: HTTPTransport, ws: Optional[WebSocketTransport] = None):
        self._http = http
        self._ws = ws
