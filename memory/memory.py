from abc import ABC, abstractmethod

import json
from typing import List

from memory.messages_operations import MessageOperations
from models.message import Message as SchemaMessage
from models.message_param import MessageLike
from models.tool_call import AssistantMessage, ToolMessage


class MemoryInterface(ABC):
    def __init__(self):
        self.messages = []

    @abstractmethod
    async def init_messages(self, limit=20):
        """Load messages from the storage."""
        pass

    @abstractmethod
    async def save(self, message: MessageLike):
        """Save message to the storage."""
        pass

    @abstractmethod
    async def saveList(self, messages: List[MessageLike]):
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
    async def delete_message(self, id):
        """Delete a specific message entry."""
        pass

    @abstractmethod
    def get_message_params(self):
        pass


class InMemoryStorage(MemoryInterface):
    def __init__(self):
        super().__init__()

    async def init_messages(self, limit=20):
        system_message = SchemaMessage(
            role="system", content="Hello! I am a helpful assistant."
        )
        self.messages.append(system_message)
        return self.messages

    async def save(self, message: MessageLike):
        self.messages.append(message)

    async def saveList(self, messages: List[MessageLike]):
        self.messages.extend(messages)

    async def get_message(self, id):
        pass

    async def set_message(self, id, message):
        pass

    async def delete_message(self, message):
        pass

    def get_message_params(self):
        return self.messages


class DatabaseStorage(MemoryInterface):
    def __init__(self):
        super().__init__()
        self.messagesOps = MessageOperations()

    async def init_messages(self, limit=20):
        db_messages = await self.messagesOps.get_latest_messages(limit)
        db_messages.reverse()
        self.messages.clear()

        self.messages.extend(db_messages)  # order by created at asc
        return db_messages

    async def save(self, message: MessageLike):
        db_message = await self.messagesOps.add_message(
            message.role, message.content, message.model_dump_json()
        )
        self.messages.append(db_message)

    async def saveList(self, messages: List[MessageLike]):
        for message in messages:
            await self.save(message)

    async def get_message(self, id):
        db_message = await self.messagesOps.get_message(id)
        return db_message

    async def set_message(self, id, message):
        # db_message = convert_to_db_message(message)
        # self.messagesOps.update_message(id, db_message)
        pass

    async def delete_message(self, id):
        await self.messagesOps.delete_message(id)
        self.messages = [message for message in self.messages if message.id != id]

    def get_message_params(self):
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
