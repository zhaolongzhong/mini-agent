from typing import List, Union, Optional

from pydantic import Field, BaseModel

from .author import Author

DEFAULT_MAX_MESSAGES = 6
MAX_ALLOWED_MESSAGES = 12


class AgentTransfer(BaseModel):
    to_agent_id: str = Field(..., description="ID of the target agent")
    message: str = Field(..., description="Message to be sent to the target agent")
    max_messages: int = Field(
        default=DEFAULT_MAX_MESSAGES,
        ge=0,  # Changed to allow 0
        le=MAX_ALLOWED_MESSAGES,
        description="Maximum number of messages to transfer. 0 means using only the message field",
    )
    context: Optional[Union[str, List]] = None


class ToolResponseWrapper(BaseModel):
    author: Optional[Author] = None
    tool_messages: Optional[List[dict]] = None
    tool_result_message: Optional[dict] = None
    agent_transfer: Optional[AgentTransfer] = None
    base64_images: list = None
