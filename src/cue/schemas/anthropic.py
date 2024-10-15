from typing import Optional, Union

from pydantic import BaseModel


class TextContent(BaseModel):
    type: str
    text: str


class ToolUseContent(BaseModel):
    type: str
    id: Optional[str]
    name: Optional[str]
    input: Optional[dict]


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class Message(BaseModel):
    id: str
    type: str
    role: str
    model: str
    content: list[Union[TextContent, ToolUseContent]]
    stop_reason: Optional[str]
    stop_sequence: Optional[str]
    usage: Usage


class AnthropicUserMessage(BaseModel):
    role: str
    content: str


class AnthropicAssistantMessage(BaseModel):
    role: str
    content: Union[list[Union[TextContent, ToolUseContent]], str]


class ToolResultContent(BaseModel):
    type: str = "tool_result"  # "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False  # https://docs.anthropic.com/en/docs/build-with-claude/tool-use#tool-execution-error


class ToolResultMessage(BaseModel):
    role: str  # it's 'user' not 'tool'
    content: list[ToolResultContent]


AnthropicMessageParam = Union[AnthropicUserMessage, AnthropicAssistantMessage, ToolResultMessage]

"""
# Tool result message example
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01D7CURZGQNURi3QzvfEJy8W", "content": "stdout:[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]\n"}]}
"""

"""
# Tool use content example
{"role": "assistant", "content": [{"type": "text", "text": "Certainly! I can use the `execute_shell_command` function to run a shell command that will make the system sleep for 8 seconds. The command we'll use is `sleep 8`, which is available on most Unix-like systems (including Linux and macOS).\n\nHere's how we'll do it:"}, {"type": "tool_use", "id": "toolu_016EeMiuVCz2wVNhPGj1KE1W", "name": "execute_shell_command", "input": {"command": "sleep 8", "wait": true}}]}
"""


def convert_to_text_content(message: AnthropicMessageParam) -> AnthropicMessageParam:
    if isinstance(message, AnthropicAssistantMessage):
        new_content = []
        for item in message.content:
            if isinstance(item, ToolUseContent):
                text = f"Tool use: {item.name}, Input: {item.input}"
                new_content.append(TextContent(type="text", text=text))
            elif isinstance(item, TextContent):
                new_content.append(item)
        message.content = new_content
        return message
    elif isinstance(message, ToolResultMessage):
        new_content = []
        user_message = AnthropicUserMessage(role="user", content="placeholder_content")
        for item in message.content:
            if isinstance(item, ToolResultContent):
                text = f"Tool result: {item.content}, Error: {item.is_error}"
                new_content.append(TextContent(type="text", text=text))
        user_message.content = new_content
        return user_message
    return message
