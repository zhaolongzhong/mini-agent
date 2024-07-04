from typing import Literal

from pydantic import BaseModel


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str
    function: FunctionCall


# Model for the message in the response choice
class ChatCompletionMessage(BaseModel):
    role: str
    name: str | None = None
    content: str | None = None  # might be None if it's tool_call
    tool_calls: list[ToolCall] | None = None


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
    finish_reason: str | None = None
    finish_details: FinishDetails | None = None  # either finish_reason or finish_details will be returned not both


class ChatCompletion(BaseModel):
    id: str
    """A unique identifier for the chat completion."""

    choices: list[Choice]
    """A list of chat completion choices.

    Can be more than one if `n` is greater than 1.
    """

    created: int
    """The Unix timestamp (in seconds) of when the chat completion was created."""

    model: str
    """The model used for the chat completion."""

    object: Literal["chat.completion"]
    """The object type, which is always `chat.completion`."""

    system_fingerprint: str | None = None
    """This fingerprint represents the backend configuration that the model runs with.

    Can be used in conjunction with the `seed` request parameter to understand when
    backend changes have been made that might impact determinism.
    """

    usage: CompletionUsage | None = None
    """Usage statistics for the completion request."""
