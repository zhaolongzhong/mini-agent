import logging
from typing import List, Optional

from ..schemas import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
)
from .transport import HTTPTransport, ResourceClient, WebSocketTransport

logger = logging.getLogger(__name__)


class ConversationClient(ResourceClient):
    """Client for conversation-related operations"""

    def __init__(self, http: HTTPTransport, ws: Optional[WebSocketTransport] = None):
        super().__init__(http, ws)
        self._default_conversation_id: Optional[str] = None

    async def create(
        self,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Conversation:
        data = ConversationCreate(title=title, metadata=metadata or {}).model_dump()
        response = await self._http.request("POST", "/conversations", data=data)
        return Conversation(**response)

    async def get(self, conversation_id: str) -> Conversation:
        response = await self._http.request("GET", f"/conversations/{conversation_id}")
        return Conversation(**response)

    async def list(self, skip: int = 0, limit: int = 50) -> List[Conversation]:
        response = await self._http.request("GET", f"/conversations?skip={skip}&limit={limit}")
        return [Conversation(**conv) for conv in response]

    async def update(self, conversation_id: str, update_data: ConversationUpdate) -> Conversation:
        response = await self._http.request("PUT", f"/conversations/{conversation_id}", data=update_data.model_dump())
        return Conversation(**response)

    async def delete(self, conversation_id: str) -> None:
        await self._http.request("DELETE", f"/conversations/{conversation_id}")

    async def create_default_conversation(self) -> Optional[str]:
        """Create a default conversation"""
        conversation = await self.create(title="default")
        if not conversation:
            return
        self._default_conversation_id = conversation.id
        return self._default_conversation_id
