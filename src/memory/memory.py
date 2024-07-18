import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

from llm_client.llm_model import ChatModel
from memory.memory_utils import load_from_memory
from memory.messages_operations import MessageOperations
from schemas.message import Message as SchemaMessage
from schemas.message_param import MessageLike
from schemas.tool_call import AssistantMessage, ToolMessage

max_messages = 20


class StorageType(Enum):
    IN_MEMORY = "in_memory"
    FILE = "file"
    DATABASE = "database"


class MemoryInterface(ABC):
    def __init__(self):
        self.messages: list[MessageLike] = []

    @abstractmethod
    async def init_messages(self, limit=max_messages):
        """Load messages from the storage."""
        pass

    @abstractmethod
    async def save(self, message: MessageLike):
        """Save message to the storage."""
        pass

    @abstractmethod
    async def saveList(self, messages: list[MessageLike]):
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
    def get_message_params(self):
        pass


class InMemoryStorage(MemoryInterface):
    def __init__(self):
        super().__init__()

    async def init_messages(self, limit=max_messages):
        return self.messages

    async def save(self, message: MessageLike):
        self.messages.append(message)

    async def saveList(self, messages: list[MessageLike]):
        self.messages.extend(messages)

    async def get_message(self, id):
        pass

    async def set_message(self, id, message):
        pass

    def get_message_params(self):
        return self.messages


class FileStorage(MemoryInterface):
    def __init__(self, name="memory.jsonl", model: ChatModel = None):
        super().__init__()
        self.memory_root_path = Path(__file__).parent
        if "jsonl" not in name:
            name += "_memory.jsonl"
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

    async def save(self, message: MessageLike):
        self.messages.append(message)
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(message.model_dump()) + "\n")

    async def saveList(self, messages: list[MessageLike]):
        for message in messages:
            await self.save(message)

    async def get_message(self, id):
        pass

    async def set_message(self, id, message):
        pass

    def get_message_params(self):
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

    async def save(self, message: MessageLike):
        db_message = await self.messagesOps.add_message(message.role, message.content, message.model_dump_json())
        self.messages.append(db_message)

    async def saveList(self, messages: list[MessageLike]):
        for message in messages:
            await self.save(message)

    async def get_message(self, id):
        db_message = await self.messagesOps.get_message(id)
        return db_message

    async def set_message(self, id, message):
        # db_message = convert_to_db_message(message)
        # self.messagesOps.update_message(id, db_message)
        pass

    def get_message_params(self) -> list[MessageLike]:
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
                    message = ToolMessage(**message_dict)
                    schema_messages.append(message)
                elif role in ["system", "user"]:
                    message = SchemaMessage(**message_dict)
                    schema_messages.append(message)
                else:
                    print(f"Invalid message_dict. msg: {msg}")
                    message_dict.update({"role": msg.role, "content": msg.content})
                    message = SchemaMessage(**message_dict)
                    schema_messages.append(message)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON for msg: {msg}")
            except Exception as e:
                print(f"An error occurred: {e}")
        return schema_messages
