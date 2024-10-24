import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic.types import Message as AnthropicMessage
from anthropic.types import MessageParam as AntropicMessageParam
from anthropic.types.beta.prompt_caching import PromptCachingBetaMessage
from openai.types.chat import ChatCompletion
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from ..llm.llm_model import ChatModel
from ..schemas import AgentConfig, AssistantMessage, CompletionResponse, StorageType, ToolResponseWrapper
from ..schemas.error import ErrorResponse
from ..schemas.message import MessageParam
from .memory_utils import load_from_memory
from .messages_operations import MessageOperations

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
                    if isinstance(msg.response, (AnthropicMessage, PromptCachingBetaMessage)):
                        result.append(msg.response)
                    elif isinstance(msg.error, ErrorResponse):
                        result.append(AntropicMessageParam(role="assistant", content=msg.error.model_dump_json()))
                    else:
                        logger.debug(f"Unexpected subclass of CompletionResponse: {type(msg)}, {model}")
                elif isinstance(msg, MessageParam):
                    result.append(msg)
                elif isinstance(msg, ToolResponseWrapper):
                    result.append(msg.tool_result_message)
                else:
                    logger.debug(f"Unexpected message type: {type(msg)}, {msg}, {model}")
            else:
                if isinstance(msg, CompletionResponse):
                    if isinstance(msg.response, ChatCompletion):
                        result.append(msg.response.choices[0].message)
                    elif isinstance(msg.error, ErrorResponse):
                        result.append(AssistantMessage(role="assistant", content=msg.error.model_dump_json()))
                    else:
                        logger.debug(f"Unexpected subclass of CompletionResponse: {type(msg)}, {model}")
                elif isinstance(msg, MessageParam):
                    result.append(msg)
                elif isinstance(msg, ToolResponseWrapper):
                    for item in msg.tool_messages:
                        result.append(item)
                else:
                    raise Exception(f"Unexpected message type: {type(msg)}, {msg}, {model}")

        return result


class FileStorage(MemoryInterface):
    def __init__(self, name="memory.jsonl", model: ChatModel = None):
        super().__init__()
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        memory_dir = os.path.join(base_dir, "logs/memory")
        os.makedirs(memory_dir, exist_ok=True)
        self.memory_root_path = memory_dir
        if "jsonl" not in name:
            name += ".jsonl"
        self.file_path = Path(f"{self.memory_root_path}/{name}")
        # clear test files
        for file in Path(self.memory_root_path).glob("*_test*"):
            if file.is_file():
                file.unlink()
        self.file_path.touch(exist_ok=True)
        messages = load_from_memory(self.file_path, model)
        self.messages = messages

    async def init_messages(self, limit=max_messages):
        return self.messages

    async def save(self, message: Dict):
        self.messages.append(message)
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(message.model_dump()) + "\n")

    async def saveList(self, messages: List[Dict]):
        for message in messages:
            await self.save(message)

    async def get_message(self, id):
        pass

    async def set_message(self, id, message):
        pass

    def get_message_params(self, model: Optional[str] = None):
        return self.messages[-max_messages:]


class DatabaseStorage(MemoryInterface):
    def __init__(self):
        super().__init__()
        self.messagesOps = MessageOperations()

    async def init_messages(self, limit=max_messages):
        db_messages = await self.messagesOps.get_latest_messages(limit)
        db_messages.reverse()
        self.messages.clear()

        self.messages.extend(db_messages)  # order by created at asc
        return db_messages

    async def save(self, message: Dict):
        db_message = await self.messagesOps.add_message(message.role, message.content, message.model_dump_json())
        self.messages.append(db_message)

    async def saveList(self, messages: List[Dict]):
        for message in messages:
            await self.save(message)

    async def get_message(self, id):
        db_message = await self.messagesOps.get_message(id)
        return db_message

    async def set_message(self, id, message):
        # db_message = convert_to_db_message(message)
        # self.messagesOps.update_message(id, db_message)
        pass

    def get_message_params(self, model: Optional[str] = None) -> List[Dict]:
        schema_messages = []
        for msg in self.messages:
            try:
                # use orginal message_json as message param
                message_json = getattr(msg, "message_json", None)
                message_dict = json.loads(message_json) if message_json else {}
                if not message_dict:
                    raise ValueError(f"Invalid msg. msg: {msg}")
                role = message_dict.get("role")
                if role == "assistant":
                    message = AssistantMessage(**message_dict)
                    schema_messages.append(message)
                elif role == "tool":
                    message = ToolMessageParam(**message_dict)
                    schema_messages.append(message)
                elif role in ["system", "user"]:
                    message = MessageParam(**message_dict)
                    schema_messages.append(message)
                else:
                    print(f"Invalid message_dict. msg: {msg}")
                    message_dict.update({"role": msg.role, "content": msg.content})
                    message = MessageParam(**message_dict)
                    schema_messages.append(message)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON for msg: {msg}")
            except Exception as e:
                print(f"An error occurred: {e}")
        return schema_messages


def setup_memory_storage(storage_type: StorageType, config: AgentConfig, session_id: str) -> MemoryInterface:
    """
    Sets up the appropriate memory storage based on the storage type.

    Args:
        storage_type (StorageType): Type of storage to use.
        config (AgentConfig): Configuration for the agent.
        session_id (str): Unique session identifier.

    Raises:
        ValueError: If an unsupported storage type is provided.

    Returns:
        MemoryInterface: An instance of the selected memory storage.
    """
    if storage_type == StorageType.FILE:
        model_id = config.model.model_id.split("/")[-1]  # Safely extract model ID
        name = f"{config.id}_{model_id}_{session_id}"
        memory = FileStorage(name=name, model=config.model)
        logger.debug(f"Initialized FileStorage with name: {name}")
    elif storage_type == StorageType.DATABASE:
        memory = DatabaseStorage()
        logger.debug("Initialized DatabaseStorage")
    elif storage_type == StorageType.IN_MEMORY:
        memory = InMemoryStorage()
        logger.debug("Initialized InMemoryStorage")
    else:
        logger.error(f"Unsupported storage type: {storage_type}")
        raise ValueError(f"Unsupported storage type: {storage_type}")

    return memory
