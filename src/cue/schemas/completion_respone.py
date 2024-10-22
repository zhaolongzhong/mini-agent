from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from ..schemas.anthropic import Message as AnthropicMessage
from ..schemas.anthropic import ToolUseContent
from ..schemas.chat_completion import ChatCompletion
from ..schemas.error import ErrorResponse


class CompletionUsage(BaseModel):
    input_tokens: int = Field(default=0, alias="prompt_tokens")
    output_tokens: int = Field(default=0, alias="completion_tokens")
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    class Config:
        populate_by_name = True  # Allows both alias and field name to be used
        extra = "ignore"  # Ignores extra fields in the input data


class InvalidResponseTypeError(Exception):
    """Raised when response type is neither AnthropicMessage nor ChatCompletion"""

    pass


class CompletionResponse:
    def __init__(
        self,
        model: str,
        response: Optional[Any] = None,
        error: Optional[Any] = None,
        metadata: Optional[Any] = None,
    ):
        self.model = model
        self.response = response
        self.error = error
        self.metadata = metadata

    def get_text(self) -> Union[str, list[dict]]:
        if self.response is None:
            return str(self.error)

        if isinstance(self.response, AnthropicMessage):
            return self.response.content[0].text
        elif isinstance(self.response, ChatCompletion):
            return self.response.choices[0].message.content
        raise InvalidResponseTypeError(
            f"Expected AnthropicMessage or ChatCompletion, got {type(self.response).__name__}"
        )

    def get_tool_calls(self) -> Optional[list[Any]]:
        if isinstance(self.response, AnthropicMessage):
            tool_calls = [
                content_item for content_item in self.response.content if isinstance(content_item, ToolUseContent)
            ]
            return tool_calls
        elif isinstance(self.response, ChatCompletion):
            return self.response.choices[0].message.tool_calls
        elif isinstance(self.error, ErrorResponse):
            return None
        raise InvalidResponseTypeError(
            f"Expected AnthropicMessage or ChatCompletion, got {type(self.response).__name__}"
        )

    def get_usage(self) -> Optional[CompletionUsage]:
        if self.response is None:
            return None

        if isinstance(self.response, AnthropicMessage):
            return CompletionUsage(**self.response.usage.model_dump())
        elif isinstance(self.response, ChatCompletion):
            usage = self.response.usage

            completion_usage = CompletionUsage(**usage.model_dump())
            if usage.completion_tokens_details:
                completion_usage.reasoning_tokens = usage.completion_tokens_details.reasoning_tokens
            if usage.prompt_tokens_details:
                completion_usage.cached_tokens = usage.prompt_tokens_details.cached_tokens
            return completion_usage
        raise InvalidResponseTypeError(
            f"Expected AnthropicMessage or ChatCompletion, got {type(self.response).__name__}"
        )

    def __str__(self):
        return f"Text: {self.get_text()}, Tools: {self.get_tool_calls()}, Usage: {self.get_usage()}"
