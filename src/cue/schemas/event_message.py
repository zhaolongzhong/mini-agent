import uuid
from enum import Enum
from typing import Union, Optional
from datetime import datetime

from pydantic import Field, BaseModel, ConfigDict, computed_field


class ErrorResponse(BaseModel):
    status: str
    detail: str


class ClientMessage(BaseModel):
    """
    Represents a client message with optional JSON data.
    """

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the message."
    )
    role: str = Field(..., description="Role of the sender.")
    content: Optional[str] = Field(None, description="Content of the message.")
    name: Optional[str] = Field(None, description="Name of author of the message.")
    message_json: Optional[str] = Field(None, description="Original JSON data used to create this message.")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the message was created.")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def created_at_iso(self) -> str:
        return self.created_at.isoformat()


class ClientConnectEventPayload(BaseModel):
    client_id: str
    connection_id: str
    message: Optional[str] = None


class PromptEventPayload(ClientMessage):
    pass


class GenericEventPayload(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the message")
    content: str
    created_at: Optional[datetime] = Field(default=datetime.now(), description="Date and time the message was created")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def created_at_iso(self) -> str:
        return self.created_at.isoformat()


class PingPoingEventPayload(BaseModel):
    type: str


class MessageEventPayload(BaseModel):
    payload: dict


class MessageChunkEventPayload(BaseModel):
    payload: dict


EventPayload = Union[
    PromptEventPayload,
    ClientConnectEventPayload,
    GenericEventPayload,
    PingPoingEventPayload,
    MessageEventPayload,
    MessageChunkEventPayload,
]


class EventMessageType(Enum):
    GENERIC = "generic"
    PROMPT = "prompt"
    ASSISTANT = "assistant"
    MESSAGE = "message"
    MESSAGE_CHUNK = "message_chunk"
    CLIENT_CONNECT = "client_connect"
    CLIENT_LEAVE = "client_leave"
    PING = "ping"
    PONG = "pong"


class EventMessage(BaseModel):
    type: EventMessageType = Field(..., description="Type of event")
    payload: EventPayload
    creator_user_id: Optional[str] = None
    client_id: Optional[str] = None
    metadata: Optional[dict] = Field(None, description="Metadata related to the event")
