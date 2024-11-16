from enum import Enum
from typing import Union, Optional

from pydantic import Field, BaseModel, ConfigDict


class EventMessageType(str, Enum):
    GENERIC = "generic"
    USER = "user"
    ASSISTANT = "assistant"
    CLIENT_CONNECT = "client_connect"
    CLIENT_DISCONNECT = "client_disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class MessagePayloadBase(BaseModel):
    message: Optional[str] = Field(None, description="Message content")
    sender: Optional[str] = Field(None, description="Sender identifier")
    recipient: Optional[str] = Field(None, description="Recipient identifier")
    websocket_request_id: Optional[str] = Field(None, description="Request tracking ID")

    model_config = ConfigDict(frozen=True)


class GenericMessagePayload(MessagePayloadBase):
    user_id: Optional[str] = Field(None, description="User identifier")


class MessagePayload(MessagePayloadBase):
    # content: Optional[str] = None
    user_id: Optional[str] = None
    payload: Optional[dict] = None
    role: str = "user"


class ClientEventPayload(MessagePayloadBase):
    client_id: str
    user_id: Optional[str] = None


class PingPongEventPayload(MessagePayloadBase):
    type: str


EventPayload = Union[
    ClientEventPayload,
    PingPongEventPayload,
    MessagePayload,
    GenericMessagePayload,
]


class EventMessage(BaseModel):
    type: EventMessageType = Field(..., description="Type of event")
    payload: EventPayload
    client_id: Optional[str] = None
    metadata: Optional[dict] = Field(None, description="Metadata related to the event")
    websocket_request_id: Optional[str] = None
