import uuid
from typing import Optional
from datetime import datetime

from pydantic import Field, BaseModel


class Metadata(BaseModel):
    is_primary: bool = False


class ConversationBase(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Metadata] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    assistant_id: Optional[str] = None
    metadata: Optional[dict] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class ConversationInDBBase(ConversationBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    updated_at: datetime

    class ConfigDict:
        from_attributes = True


class Conversation(ConversationInDBBase):
    pass
