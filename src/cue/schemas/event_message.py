import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    status: str
    detail: str


# Shared properties for Message
class ClientMessageBase(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    content: Optional[str] = None
    message_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ClientMessageCreate(ClientMessageBase):
    role: str
    content: Optional[str] = None


class ClientMessage(ClientMessageBase):
    # id: UUID4
    id: str

    model_config = ConfigDict(from_attributes=True)


class ClientConnectEventPayload(BaseModel):
    client_id: str
    connection_id: str
    message: Optional[str] = None


class PromptEventPayload(ClientMessage):
    pass


class AgentEventPayload(ClientMessage):
    pass


class GenericEventPayload(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the message")
    content: str
    created_at: Optional[datetime] = Field(default=datetime.now(), description="Date and time the message was created")


class PingPoingEventPayload(BaseModel):
    type: str


class MessageEventPayload(BaseModel):
    json_dict: dict


class ConversationEventPayload(BaseModel):
    json_dict: dict


class MessageChunkEventPayload(BaseModel):
    json_dict: dict


EventPayload = Union[
    PromptEventPayload,
    ClientConnectEventPayload,
    GenericEventPayload,
    PingPoingEventPayload,
    MessageEventPayload,
    MessageChunkEventPayload,
    ConversationEventPayload,
]


class EventMessageType(Enum):
    GENERIC = "generic"
    PROMPT = "prompt"
    MESSAGE = "message"
    MESSAGE_CHUNK = "message_chunk"
    CONVERSATION = "conversation"
    CLIENT_CONNECT = "client_connect"
    CLIENT_LEAVE = "client_leave"
    AGENT = "agent"
    PING = "ping"
    PONG = "pong"


class EventMessage(BaseModel):
    type: EventMessageType = Field(..., description="Type of event")
    payload: EventPayload
    creator_user_id: Optional[str] = None
    client_id: Optional[str] = None
    metadata: Optional[dict] = Field(None, description="Metadata related to the event")
