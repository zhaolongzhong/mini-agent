from enum import Enum
from typing import Union, Optional

from pydantic import Field, BaseModel


class EventMessageType(str, Enum):
    GENERIC = "generic"
    USER = "user"
    ASSISTANT = "assistant"
    MESSAGE_CHUNK = "message_chunk"
    CLIENT_CONNECT = "client_connect"
    CLIENT_LEAVE = "client_leave"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class GenericMessagePayload(BaseModel):
    message: str
    sender: Optional[str] = None
    recipient: str
    websocket_request_id: Optional[str] = None


class CompletionMessagePayload(BaseModel):
    """
    Represents a client message with optional JSON data.
    """

    content: Optional[str] = Field(None, description="Content of the message.")
    role: Optional[str] = Field(None, description="Role of the sender.")
    name: Optional[str] = Field(
        None,
        description="Name of author of the message.",
    )
    payload: Optional[dict] = Field(None, description="Original JSON data used to create this message.")
    sender: Optional[str] = None
    recipient: str
    websocket_request_id: Optional[str] = None


class ClientEventPayload(BaseModel):
    client_id: str
    session_id: str
    message: Optional[str] = None


class PingPongEventPayload(BaseModel):
    type: str
    recipient: Optional[str] = None


EventPayload = Union[
    ClientEventPayload,
    PingPongEventPayload,
    CompletionMessagePayload,
    GenericMessagePayload,
]


class EventMessage(BaseModel):
    type: EventMessageType = Field(..., description="Type of event")
    payload: EventPayload
    client_id: Optional[str] = None
    metadata: Optional[dict] = Field(None, description="Metadata related to the event")
    websocket_request_id: Optional[str] = None
