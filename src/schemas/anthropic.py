from pydantic import BaseModel


class TextContent(BaseModel):
    type: str
    text: str


class ToolUseContent(BaseModel):
    type: str
    id: str | None
    name: str | None
    input: dict | None


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class Message(BaseModel):
    id: str
    type: str
    role: str
    model: str
    content: list[TextContent | ToolUseContent]
    stop_reason: str | None
    stop_sequence: str | None
    usage: Usage


class AnthropicUserMessage(BaseModel):
    role: str
    content: str


class AnthropicAssistantMessage(BaseModel):
    role: str
    content: list[TextContent | ToolUseContent]


class ToolResultContent(BaseModel):
    type: str = "tool_result"  # "tool_result"
    tool_use_id: str
    content: str


class ToolResultMessage(BaseModel):
    role: str  # it's 'user' not 'tool'
    content: list[ToolResultContent]


MessageParam = Message | AnthropicAssistantMessage | ToolResultMessage

"""
# Tool result message example
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01D7CURZGQNURi3QzvfEJy8W", "content": "stdout:[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]\n"}]}
"""

"""
# Tool use content example
{"role": "assistant", "content": [{"type": "text", "text": "Certainly! I can use the `execute_shell_command` function to run a shell command that will make the system sleep for 8 seconds. The command we'll use is `sleep 8`, which is available on most Unix-like systems (including Linux and macOS).\n\nHere's how we'll do it:"}, {"type": "tool_use", "id": "toolu_016EeMiuVCz2wVNhPGj1KE1W", "name": "execute_shell_command", "input": {"command": "sleep 8", "wait": true}}]}
"""
