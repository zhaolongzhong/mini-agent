from typing import Any
from pydantic import BaseModel


class MessageBase(BaseModel):
    role: str
    content: str


class Message(MessageBase):
    tool_calls: list[Any] | None = None
