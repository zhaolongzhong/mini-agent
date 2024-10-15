import uuid
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .task import Task


class Context(BaseModel):
    task: Union[Task, str, None] = None

    def filtered_context(self) -> dict:
        # Filter out None fields
        context_dict = {k: v for k, v in self.model_dump().items() if v is not None}
        if "default_working_directory" not in context_dict or context_dict["default_working_directory"] is None:
            context_dict["default_working_directory"] = "~/cue"
        return context_dict


class Metadata(BaseModel):
    enable_developer_mode: bool = False
    enable_turbo_mode: bool = False
    enable_temporary_chat: bool = False
    model: str = "gpt-4o"
    temperature: Optional[float] = 0.8
    platform: Optional[str] = None  # macos, linux, windows ios, web, android
    context_window_size: Optional[int] = None


# Shared properties
class ConversationBase(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    description: Optional[str] = None
    is_archived: bool = False
    is_starred: Optional[bool] = False
    workspace_id: Optional[str] = None
    assistant_id: Optional[str] = None


# Properties to receive on item creation
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    assistant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    metadata: Optional[Metadata] = Metadata()


# Properties to receive on item update
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None
    is_starred: Optional[bool] = None
    assistant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    context: Optional[Context] = None
    metadata: Optional[Metadata] = None


# Properties shared by models stored in DB
class ConversationInDBBase(ConversationBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    context: Optional[Context] = None
    metadata: Optional[Metadata] = None
    is_archived: Optional[bool] = False
    is_starred: Optional[bool] = False
    assistant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_system_detail_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Conversation(ConversationBase):
    context: Optional[Context] = None
    metadata: Optional[Metadata] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Properties properties stored in DB
class ConversationInDB(ConversationInDBBase):
    pass
