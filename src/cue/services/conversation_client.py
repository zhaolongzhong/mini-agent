# src/cue/memory/client.py
import logging
from typing import List, Optional

from ..schemas import (
    Message,
    Conversation,
    MessageCreate,
    MessageUpdate,
    ConversationCreate,
    ConversationUpdate,
)
from .transport import ResourceClient

logger = logging.getLogger(__name__)


class ConversationClient(ResourceClient):
    """Client for conversation-related operations"""

    async def create(
        self,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Conversation:
        data = ConversationCreate(title=title, metadata=metadata or {}).model_dump()
        response = await self._http.request("POST", "/conversations/", data=data)
        return Conversation(**response)

    async def get(self, conversation_id: str) -> Conversation:
        response = await self._http.request("GET", f"/conversations/{conversation_id}")
        return Conversation(**response)

    async def list(self, skip: int = 0, limit: int = 50) -> List[Conversation]:
        response = await self._http.request("GET", f"/conversations/?skip={skip}&limit={limit}")
        return [Conversation(**conv) for conv in response]

    async def update(self, conversation_id: str, update_data: ConversationUpdate) -> Conversation:
        response = await self._http.request("PUT", f"/conversations/{conversation_id}", data=update_data.model_dump())
        return Conversation(**response)

    async def delete(self, conversation_id: str) -> None:
        await self._http.request("DELETE", f"/conversations/{conversation_id}")


class MessageClient(ResourceClient):
    """Client for message-related operations"""

    async def create(self, message: MessageCreate) -> Message:
        response = await self._http.request("POST", "/messages/", data=message.model_dump())
        return Message(**response)

    async def get(self, message_id: str) -> Message:
        response = await self._http.request("GET", f"/messages/{message_id}")
        return Message(**response)

    async def get_conversation_messages(self, conversation_id: str, skip: int = 0, limit: int = 100) -> List[Message]:
        response = await self._http.request(
            "GET", f"/conversation/{conversation_id}/messages", params={"skip": skip, "limit": limit}
        )
        return [Message(**msg) for msg in response]

    async def update(self, message_id: str, update_data: MessageUpdate) -> Message:
        response = await self._http.request("PUT", f"/messages/{message_id}", data=update_data.model_dump())
        return Message(**response)

    async def delete(self, message_id: str) -> None:
        await self._http.request("DELETE", f"/messages/{message_id}")

    async def send_websocket_message(self, message: dict[str, any]) -> None:
        """
        Send a message through WebSocket connection.

        Args:
            message (Dict[str, Any]): The message to send through the WebSocket connection

        Raises:
            ConnectionError: If WebSocket connection is not established
            RuntimeError: If sending message fails
        """
