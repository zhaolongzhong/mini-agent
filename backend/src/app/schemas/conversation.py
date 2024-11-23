import uuid
from datetime import datetime

from pydantic import Field, BaseModel


class Metadata(BaseModel):
    is_primary: bool | None = False


# Shared properties
class ConversationBase(BaseModel):
    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str | None = None


class ConversationCreate(BaseModel):
    title: str | None = None
    assistant_id: str | None = None
    metadata: Metadata | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    metadata: Metadata | None = None


class ConversationInDBBase(ConversationBase):
    metadata: Metadata | None = None
    created_at: datetime
    updated_at: datetime

    class ConfigDict:
        from_attributes = True


class Conversation(ConversationInDBBase):
    pass
