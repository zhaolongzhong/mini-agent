import uuid
from typing import Optional
from datetime import datetime

from pydantic import Field, BaseModel


class AssistantBase(BaseModel):
    name: str
    is_primary: Optional[bool] = False


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
