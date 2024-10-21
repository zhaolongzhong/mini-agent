from typing import Any, Optional, Union

from ..schemas.anthropic import Message as AnthropicMessage
from ..schemas.anthropic import ToolUseContent
from ..schemas.chat_completion import ChatCompletion


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
        else:
            return f"Unknown response type: {type(self.response).__name__}"

    def get_tool_calls(self) -> list[Any]:
        if isinstance(self.response, AnthropicMessage):
            tool_calls = [
                content_item for content_item in self.response.content if isinstance(content_item, ToolUseContent)
            ]
            return tool_calls
        elif isinstance(self.response, ChatCompletion):
            return self.response.choices[0].message.tool_calls
        return []

    def __str__(self):
        return f"Text: {self.get_text()}, Tools: {self.get_tool_calls()}"
