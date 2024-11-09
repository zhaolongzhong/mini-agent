from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class Author(BaseModel):
    role: str
    name: Optional[str] = None
    metadata: Optional[dict] = None


class Content(BaseModel):
    content: Optional[str] = None


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

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def created_at_iso(self) -> str:
        return self.created_at.isoformat()

    @computed_field
    @property
    def updated_at_iso(self) -> str:
        return self.updated_at.isoformat()


class MessageChunk(BaseModel):
    id: str
    content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def created_at_iso(self) -> str:
        return self.created_at.isoformat()

    @computed_field
    @property
    def updated_at_iso(self) -> str:
        return self.updated_at.isoformat()


class MessageParam(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
