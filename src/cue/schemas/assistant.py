import uuid
from typing import Union, Optional
from datetime import datetime

from pydantic import Field, BaseModel


class Metadata(BaseModel):
    is_primary: Optional[bool] = None
    model: Optional[str] = None
    instruction: Optional[str] = None
    description: Optional[str] = None
    max_turns: Optional[int] = None
    context: Optional[dict] = None
    tools: Optional[list[Union[str, list]]] = None


class AssistantBase(BaseModel):
    name: str
    metadata: Metadata | None = None


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(AssistantBase):
    pass


class AssistantInDBBase(AssistantBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    updated_at: datetime

    class ConfigDict:
        from_attributes = True


class Assistant(AssistantInDBBase):
    pass
