import logging
from typing import Any, Dict, List, Optional

import aiohttp
from httpx import HTTPError
from pydantic import TypeAdapter

from ..config import get_settings
from ..schemas.message import Message, MessageCreate, MessageUpdate
from ..schemas.assistant import Assistant, AssistantCreate
from ..schemas.conversation import Conversation, ConversationCreate, ConversationUpdate
from ..schemas.event_message import EventMessage, EventMessageType
from ..schemas.assistant_memory import (
    AssistantMemory,
    AssistantMemoryCreate,
    AssistantMemoryUpdate,
    RelevantMemoriesResponse,
)

logger = logging.getLogger(__name__)


class MemoryServiceClient:
    def __init__(self, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = base_url or self.settings.API_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.event_handlers: Dict[EventMessageType, callable] = {}
        self.default_assistant_id: Optional[str] = None

    async def connect(self) -> None:
        """Establish connection to the service"""
        if self.session and not self.session.closed:
            return

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def disconnect(self) -> None:
        """Close all connections"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.ws and not self.ws.closed:
            await self.ws.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make HTTP request to the API"""
        if not self.session or self.session.closed:
            await self.connect()

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

    async def create_default_assistant(self):
        """Create an default assistant to persist memories across multiple conversation"""
        assistant = await self.create_assistant(AssistantCreate(name="default"))
        self.default_assistant_id = assistant.id

    async def get_safe_assistant_id(self, assistant_id: Optional[str] = None) -> str:
        """If no assistant id provided, use default assistant"""
        if not assistant_id:
            if not self.default_assistant_id:
                await self.create_default_assistant()
            assistant_id = self.default_assistant_id
        return assistant_id

    # Conversation Management
    async def create_conversation(
        self,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Conversation:
        """Create a new conversation"""
        data = ConversationCreate(title=title, metadata=metadata or {}).model_dump()
        response = await self._make_request("POST", "/conversations/", data)
        return Conversation(**response)

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get conversation by ID"""
        response = await self._make_request("GET", f"/conversations/{conversation_id}")
        return Conversation(**response)

    async def get_conversations(self, skip: int = 0, limit: int = 50) -> List[Conversation]:
        """Get list of conversations"""
        response = await self._make_request("GET", f"/conversations/?skip={skip}&limit={limit}")
        return [Conversation(**conv) for conv in response]

    async def update_conversation(self, conversation_id: str, update_data: ConversationUpdate) -> Conversation:
        response = await self._make_request("PUT", f"/conversations/{conversation_id}", update_data.model_dump())
        return Conversation(**response)

    async def delete_conversation(self, conversation_id: str) -> None:
        await self._make_request("DELETE", f"/conversations/{conversation_id}")

    # Message Management
    async def create_message(self, message: MessageCreate) -> Message:
        """Create a new message"""
        response = await self._make_request("POST", "/messages/", message.model_dump())
        return Message(**response)

    async def get_message(self, message_id: str) -> Message:
        """Get message by ID"""
        response = await self._make_request("GET", f"/messages/{message_id}")
        return Message(**response)

    async def get_conversation_messages(self, conversation_id: str, skip: int = 0, limit: int = 100) -> List[Message]:
        """Get messages for a conversation"""
        response = await self._make_request(
            "GET", f"/conversation/{conversation_id}/messages?skip={skip}&limit={limit}"
        )
        return [Message(**msg) for msg in response]

    async def update_message(self, message_id: str, update_data: MessageUpdate) -> Message:
        """Update message"""
        response = await self._make_request("PUT", f"/messages/{message_id}", update_data.model_dump())
        return Message(**response)

    async def delete_message(self, message_id: str) -> None:
        """Delete message"""
        await self._make_request("DELETE", f"/messages/{message_id}")

    # Assistant Management
    async def create_assistant(self, assistant: AssistantCreate) -> Assistant:
        """Create a new assistant with name, return one if there is an existing one."""
        response = await self._make_request("POST", "/assistants/", assistant.model_dump())
        return Assistant(**response)

    async def get_assistant(self, assistant_id: str) -> Assistant:
        """Get assistant by ID"""
        response = await self._make_request("GET", f"/assistants/{assistant_id}")
        return Assistant(**response)

    async def get_assistants(self, skip: int = 0, limit: int = 100) -> List[Assistant]:
        """Get list of assistants"""
        response = await self._make_request("GET", f"/assistants/?skip={skip}&limit={limit}")
        return [Assistant(**asst) for asst in response]

    async def delete_assistant(self, assistant_id: str) -> None:
        """Delete assistant"""
        await self._make_request("DELETE", f"/assistants/{assistant_id}")

    # Memory Management
    async def create_memory(self, memory: AssistantMemoryCreate, assistant_id: Optional[str] = None) -> AssistantMemory:
        """Create a new assistant memory"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        response = await self._make_request("POST", f"/assistants/{assistant_id}/memories", memory.model_dump())
        return AssistantMemory(**response)

    async def get_memory(self, memory_id: str, assistant_id: Optional[str] = None) -> Optional[AssistantMemory]:
        """Get memory by ID"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        response = await self._make_request("GET", f"/assistants/{assistant_id}/memories/{memory_id}")
        if response:
            return AssistantMemory(**response)
        return None

    async def get_memories(
        self, assistant_id: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[AssistantMemory]:
        """Get memories for an assistant in desc order by updated_at"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        response = await self._make_request("GET", f"/assistants/{assistant_id}/memories?skip={skip}&limit={limit}")
        return [AssistantMemory(**memory) for memory in response]

    async def update_memory(
        self,
        memory_id: str,
        memory: AssistantMemoryUpdate,
        assistant_id: Optional[str] = None,
    ) -> AssistantMemory:
        """Update memory"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        response = await self._make_request(
            "PUT", f"/assistants/{assistant_id}/memories/{memory_id}", memory.model_dump()
        )
        return AssistantMemory(**response)

    async def delete_memory(self, assistant_id: str, memory_id: str) -> None:
        """Delete memory"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        await self._make_request("DELETE", f"/assistants/{assistant_id}/memories/{memory_id}")

    async def delete_memories(self, memory_ids: List[str], assistant_id: Optional[str] = None) -> Dict[str, Any]:
        """Bulk delete multiple memories for an assistant."""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        response = await self._make_request(
            "DELETE", f"/assistants/{assistant_id}/memories/", data={"memory_ids": memory_ids}
        )
        return response

    async def search_memories(
        self, query: str, limit: int = 5, assistant_id: Optional[str] = None
    ) -> RelevantMemoriesResponse:
        """Search memories by query"""
        assistant_id = await self.get_safe_assistant_id(assistant_id)
        validated_limit = min(max(limit, 1), 20)

        params = (
            {
                "query": query,
                "limit": validated_limit,
            },
        )
        self.memories_adapter = TypeAdapter(RelevantMemoriesResponse)
        try:
            response = await self._make_request(
                method="POST", endpoint=f"/assistants/{assistant_id}/memories/search", params=params
            )

            # Parse the response into a RelevantMemoriesResponse object
            return self.memories_adapter.validate_python(response)

        except ValueError as e:
            raise ValueError(f"Failed to parse memory search response: {e}")
        except Exception as e:
            raise Exception(f"Memory search failed: {e}")

    # Event Handling
    def register_event_handler(self, event_type: EventMessageType, handler: callable) -> None:
        """Register handler for specific event type"""
        self.event_handlers[event_type] = handler

    async def handle_event(self, event_message: EventMessage) -> None:
        """Handle incoming event message"""
        if event_message.type in self.event_handlers:
            await self.event_handlers[event_message.type](event_message)
        else:
            logger.debug(f"No handler for event type: {event_message.type}")
