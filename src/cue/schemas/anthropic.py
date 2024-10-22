from typing import Optional

from pydantic import BaseModel


class TextContent(BaseModel):
    type: str
    text: str


class ToolUseContent(BaseModel):
    type: str
    id: Optional[str]
    name: Optional[str]
    input: Optional[dict]


class ToolResultContent(BaseModel):
    type: str = "tool_result"  # "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False  # https://docs.anthropic.com/en/docs/build-with-claude/tool-use#tool-execution-error


class ToolResultMessage(BaseModel):
    role: str  # it's 'user' not 'tool'
    content: list[ToolResultContent]
