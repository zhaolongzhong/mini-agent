import time
import logging
from typing import Any, Dict, Callable, Optional

from websockets.exceptions import WebSocketException

from src.app.core.config import get_settings
from src.app.core.security import create_access_token
from src.app.schemas.event_message import (
    EventMessage,
    EventMessageType,
    PingPongEventPayload,
    GenericMessagePayload,
)


class ClientWrapper:
    def __init__(
        self,
        client_id: str,
        user_id: str,
        assistant_id: Optional[str] = None,
        auto_connect: bool = True,
    ):
        from fastapi.testclient import TestClient

        from src.app.main import app

        self.client = TestClient(app)
        self.client_id = client_id
        self.user_id = user_id
        self.assistant_id = assistant_id
        self.websocket = None
        self._is_connected = False
        self.access_token = None

        if auto_connect:
            self.login()
            self.connect()

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self.websocket is not None

    def login(self) -> str:
        """Generate new access token"""
        self.access_token = create_access_token(settings=get_settings(), subject=self.user_id)
        return self.access_token

    def connect(self) -> None:
        """Explicitly connect the websocket client"""
        if self._is_connected:
            return

        if not self.access_token:
            self.login()

        url = f"/api/v1/ws/{self.client_id}"
        if self.assistant_id:
            url += f"?runner_id={self.assistant_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            # Connect without using context manager
            ws_connection = self.client.websocket_connect(url, headers=headers)
            self.websocket = ws_connection.__enter__()

            # Verify connection
            response = self.websocket.receive_json()
            if response["type"] != EventMessageType.CLIENT_CONNECT or response["client_id"] != self.client_id:
                self.disconnect()
                raise WebSocketException("Failed to verify connection")

            self._is_connected = True

        except Exception as e:
            self.disconnect()
            raise WebSocketException(f"Failed to connect: {str(e)}")

    def disconnect(self) -> None:
        """Clean up resources and close the connection"""
        if self.websocket:
            try:
                if self._is_connected:
                    self.websocket.__exit__(None, None, None)
            except Exception as e:
                logging.error(f"Error closing websocket: {e}")
            finally:
                self._is_connected = False
                self.websocket = None

    def clean_up(self) -> None:
        self.disconnect()

    def send_message(self, recipient: str, message: str) -> None:
        """Send a message to a specific recipient"""
        if not self.is_connected:
            raise RuntimeError("Cannot send message: WebSocket is not connected")

        event = EventMessage(
            client_id=self.client_id,
            type=EventMessageType.GENERIC.value,
            payload=GenericMessagePayload(type=EventMessageType.GENERIC, recipient=recipient, message=message),
        )
        self.websocket.send_text(event.model_dump_json())

    def send_event(self, event: EventMessage) -> None:
        """Send a message to a specific recipient"""
        if not self.is_connected:
            raise RuntimeError("Cannot send message: WebSocket is not connected")

        self.websocket.send_text(event.model_dump_json())

    def send_ping(self) -> None:
        """Send a ping message"""
        if not self.is_connected:
            raise RuntimeError("Cannot send ping: WebSocket is not connected")

        event = EventMessage(
            client_id=self.client_id, type=EventMessageType.PING.value, payload=PingPongEventPayload(type="PING")
        )
        self.websocket.send_text(event.model_dump_json())

    def receive_message(self) -> Dict[str, Any]:
        """Receive a message"""
        if not self.is_connected:
            raise RuntimeError("Cannot receive message: WebSocket is not connected")

        return self.websocket.receive_json()

    def has_message(self) -> bool:
        """Check if there's a message available without blocking"""
        if not self.is_connected:
            raise RuntimeError("Cannot check messages: WebSocket is not connected")

        try:
            # Try to receive a message
            _message = self.websocket.receive_text(0)
            return True
        except Exception:
            return False

    def reconnect(self) -> None:
        """Reconnect the websocket client"""
        self.disconnect()
        self.connect()


def wait_for_message_with_predicate(
    client: "ClientWrapper",
    predicate: Callable[[Dict[str, Any]], bool],
    timeout: float = 5.0,
    retry_interval: float = 0.1,
) -> Optional[Dict[str, Any]]:
    """Wait for a message that satisfies the given predicate.

    Args:
        client: The ClientWrapper instance to receive messages from
        predicate: Function that takes a message and returns True if it matches
        timeout: Maximum time to wait in seconds
        retry_interval: Time to wait between retries in seconds

    Returns:
        The matching message or None if timeout occurs
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            msg = client.receive_message()
            if predicate(msg):
                return msg
        except Exception:
            time.sleep(retry_interval)
            continue
    return None


# Common message predicates
def is_client_disconnect(client_id: str) -> Callable[[Dict[str, Any]], bool]:
    """Create a predicate for client disconnect messages."""
    return lambda msg: (msg["type"] == EventMessageType.CLIENT_DISCONNECT and msg["client_id"] == client_id)


def is_client_connect(client_id: str) -> Callable[[Dict[str, Any]], bool]:
    """Create a predicate for client connect messages."""
    return lambda msg: (msg["type"] == EventMessageType.CLIENT_CONNECT and msg["client_id"] == client_id)
