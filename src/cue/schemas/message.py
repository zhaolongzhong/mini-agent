from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel


class MessageParam(BaseModel):
    content: str
    role: str
    name: Optional[str] = None


class Author(BaseModel):
    name: Optional[str] = None
    role: str
    metadata: Optional[dict] = None


class Content(BaseModel):
    text: Optional[str] = None


class Metadata(BaseModel):
    model: Optional[str] = ""
    chat_completion_message: Optional[Any] = None
    anthropic_message: Optional[Any] = None


class MessageBase(BaseModel):
    conversation_id: str
    author: Optional[Author] = None
    content: Optional[Content] = None
    metadata: Optional[Metadata] = None


class MessageCreate(MessageBase):
    pass


class MessageUpdate(MessageBase):
    pass


class Message(MessageBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class ConfigDict:
        from_attributes = True
