import uuid
from typing import Optional

from pydantic import Field, BaseModel


class Metadata(BaseModel):
    pass


class ConversationBase(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class Conversation(ConversationBase):
    pass
