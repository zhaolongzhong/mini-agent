from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel


class Author(BaseModel):
    name: str | None = None
    role: str
    metadata: dict | None = None


class Content(BaseModel):
    text: str | None = None


class Metadata(BaseModel):
    model: str | None = ""
    chat_completion_message: Any | None = None
    anthropic_message: Any | None = None


class MessageBase(BaseModel):
    conversation_id: str
    author: Author | None = None
    content: Content | None = None
    metadata: Optional[Metadata]


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
