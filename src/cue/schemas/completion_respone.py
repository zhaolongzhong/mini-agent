from typing import Any, Optional, Union

from anthropic.types import (
    Message as AnthropicMessage,
)
from anthropic.types import ToolUseBlock
from anthropic.types.beta.prompt_caching import PromptCachingBetaMessage
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from pydantic import BaseModel, ConfigDict, Field

from ..schemas.error import ErrorResponse

ToolCallToolUseBlock = Union[ChatCompletionMessageToolCall, ToolUseBlock]


class CompletionUsage(BaseModel):
    input_tokens: int = Field(default=0, alias="prompt_tokens")
    output_tokens: int = Field(default=0, alias="completion_tokens")

    # https://platform.openai.com/docs/guides/prompt-caching/requirements
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    # https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    model_config = ConfigDict(
        populate_by_name=True,  # Allows both alias and field name to be used
        extra="ignore",  # Ignores extra fields in the input data
    )


class InvalidResponseTypeError(Exception):
    """Raised when response type is neither AnthropicMessage nor ChatCompletion"""

    pass


class CompletionResponse:
    def __init__(
        self,
        model: str,
        author: Optional[Any],
        response: Optional[Any] = None,
        error: Optional[Any] = None,
        metadata: Optional[Any] = None,
    ):
        self.author = author
        self.model = model
        self.response = response
        self.error = error
        self.metadata = metadata

    def get_text(self) -> Union[str, list[dict]]:
        if self.response is None:
            return str(self.error)

        if isinstance(self.response, (AnthropicMessage, PromptCachingBetaMessage)):
            return self.response.content[0].text
        elif isinstance(self.response, ChatCompletion):
            return self.response.choices[0].message.content
        raise InvalidResponseTypeError(
            f"Expected AnthropicMessage or ChatCompletion, got {type(self.response).__name__}"
        )

    def get_tool_calls(self) -> Optional[list[Any]]:
        if isinstance(self.response, (AnthropicMessage, PromptCachingBetaMessage)):
            tool_calls = [
                content_item for content_item in self.response.content if isinstance(content_item, ToolUseBlock)
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

        if isinstance(self.response, (AnthropicMessage, PromptCachingBetaMessage)):
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
            f"Expected AnthropicMessage or ChatCompletion, got {type(self.response).__name__}. Response: \n{self.response}"
        )

    def __str__(self):
        return f"Text: {self.get_text()}, Tools: {self.get_tool_calls()}, Usage: {self.get_usage()}"
