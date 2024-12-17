import uuid
from typing import Union, Optional
from datetime import datetime

from pydantic import Field, BaseModel


class AssistantMetadata(BaseModel):
    is_primary: Optional[bool] = None
    model: Optional[str] = None
    instruction: Optional[str] = None
    description: Optional[str] = None
    max_turns: Optional[int] = None
    context: Optional[Union[dict, str]] = None
    tools: Optional[list[Union[str, list]]] = None


class AssistantBase(BaseModel):
    name: str
    metadata: Optional[AssistantMetadata] = None


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(AssistantBase):
    name: Optional[str] = None
    metadata: Optional[AssistantMetadata] = None


class AssistantInDBBase(AssistantBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    updated_at: datetime

    class ConfigDict:
        from_attributes = True


class Assistant(AssistantInDBBase):
    pass
