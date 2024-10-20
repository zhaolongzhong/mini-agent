from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class Function(BaseModel):
    arguments: str
    name: str


class ToolCall(BaseModel):
    """
    https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion_message_tool_call.py
    """

    id: str
    type: str
    function: Function


# Model for the message in the response choice
class ChatCompletionMessage(BaseModel):
    """
    https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion_message.py
    """

    role: str
    name: Optional[str] = None
    content: Optional[str] = None  # might be None if it's tool_call
    refusal: Optional[str] = None
    """The refusal message generated by the model."""
    tool_calls: Optional[list[ToolCall]] = None


class FinishDetails(BaseModel):
    type: str  # e.g. max_tokens


class CompletionUsage(BaseModel):
    completion_tokens: int
    """Number of tokens in the generated completion."""

    prompt_tokens: int
    """Number of tokens in the prompt."""

    total_tokens: int
    """Total number of tokens used in the request (prompt + completion)."""


# Model for the choice in the response
class Choice(BaseModel):
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = None
    finish_details: Optional[FinishDetails] = None  # either finish_reason or finish_details will be returned not both


class ChatCompletion(BaseModel):
    id: Optional[str] = None  # gemini returns None
    """A unique identifier for the chat completion."""

    choices: list[Choice]
    """A list of chat completion choices.

    Can be more than one if `n` is greater than 1.
    """

    created: Optional[int] = None  # gemini returns None
    """The Unix timestamp (in seconds) of when the chat completion was created."""

    model: str
    """The model used for the chat completion."""

    object: Literal["chat.completion"]
    """The object type, which is always `chat.completion`."""

    system_fingerprint: Optional[str] = None
    """This fingerprint represents the backend configuration that the model runs with.

    Can be used in conjunction with the `seed` request parameter to understand when
    backend changes have been made that might impact determinism.
    """

    usage: Optional[CompletionUsage] = None
    """Usage statistics for the completion request."""


class ErrorResponse(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ToolMessage(BaseModel):
    content: str
    """The content of the tool message."""
    role: str = "tool"
    tool_call_id: str
    """Tool call that this message is responding to."""

    @field_validator("role", mode="before")
    def validate_role(cls, value):
        if value not in ["tool"]:
            raise ValueError('Role must be "tool"')
        return value
