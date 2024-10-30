import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from openai.types.chat import ChatCompletion

from ..schemas import AssistantMessage, CompletionResponse, ToolResponseWrapper
from ..schemas.error import ErrorResponse
from ..schemas.message import MessageParam

max_messages = 20

logger = logging.getLogger(__name__)


class MemoryInterface(ABC):
    def __init__(self):
        self.messages: List[Dict] = []

    @abstractmethod
    async def init_messages(self, limit=max_messages):
        """Load messages from the storage."""
        pass

    @abstractmethod
    async def save(self, message: Dict):
        """Save message to the storage."""
        pass

    @abstractmethod
    async def saveList(self, messages: List[Dict]):
        """Save messages to the storage."""
        pass

    @abstractmethod
    async def get_message(self, id):
        """Retrieve a specific message entry."""
        pass

    @abstractmethod
    async def set_message(self, id, message):
        """Set or update a specific message entry."""
        pass

    @abstractmethod
    def get_message_params(self, model: Optional[str] = None):
        pass


class InMemoryStorage(MemoryInterface):
    def __init__(self):
        super().__init__()

    async def init_messages(self, limit=max_messages):
        return self.messages

    async def save(self, message: Any):
        self.messages.append(message)

    async def saveList(self, messages: list[Any]):
        self.messages.extend(messages)

    async def get_message(self, id):
        pass

    async def set_message(self, id, message):
        pass

    def get_message_params(self, model: Optional[str] = None) -> List[BaseModel]:
        result = []
        for msg in self.messages:
            if model and "claude" in model:
                if isinstance(msg, CompletionResponse):
                    result.append(msg.to_params())
                elif isinstance(msg, MessageParam):
                    result.append(msg)
                elif isinstance(msg, ToolResponseWrapper):
                    result.append(msg.tool_result_message)
                else:
                    logger.debug(f"Unexpected message type: {type(msg)}, {msg}, {model}")
            else:
                if isinstance(msg, CompletionResponse):
                    if isinstance(msg.response, ChatCompletion):
                        result.append(msg.to_params())
                    elif isinstance(msg.error, ErrorResponse):
                        result.append(AssistantMessage(role="assistant", content=msg.error.model_dump_json()))
                    else:
                        logger.debug(f"Unexpected subclass of CompletionResponse: {type(msg)}, {model}")
                elif isinstance(msg, MessageParam):
                    result.append(msg)
                elif isinstance(msg, ToolResponseWrapper):
                    for item in msg.tool_messages:
                        result.append(item)
                elif isinstance(msg, dict):
                    result.append(msg)
                elif hasattr(msg, "role") and msg.role == "user":
                    # ChatCompletionUserMessageParam
                    result.append(msg)
                else:
                    raise Exception(f"Unexpected message type: {type(msg)}, {msg}, {model}")

        return result
