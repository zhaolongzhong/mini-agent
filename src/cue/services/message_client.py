import logging
from typing import List

from ..schemas import Message, MessageCreate, MessageUpdate
from .transport import ResourceClient

logger = logging.getLogger(__name__)


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
