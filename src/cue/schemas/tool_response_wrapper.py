from typing import List, Optional

from pydantic import BaseModel

from .anthropic import ToolResultMessage
from .chat_completion import ToolMessage


class ToolResponseWrapper(BaseModel):
    tool_messages: Optional[List[ToolMessage]] = None
    tool_result_message: Optional[ToolResultMessage] = None
