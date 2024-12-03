import uuid
from typing import Optional
from datetime import datetime

from pydantic import Field, BaseModel


class LearningState(BaseModel):
    personality_traits: dict = Field(default_factory=dict)
    principles: dict = Field(default_factory=dict)
    world_model: dict = Field(default_factory=dict)
    emotional_state: dict = Field(default_factory=dict)
    capabilities: dict = Field(default_factory=dict)
    version: str = "1.0"
    last_consolidated: datetime = Field(default_factory=datetime.utcnow)

class Metadata(BaseModel):
    is_primary: bool = False
    learning: Optional[LearningState] = None


class AssistantBase(BaseModel):
    name: str
    metadata: Optional[Metadata] = None


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
