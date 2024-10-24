from typing import List, Optional, Union

from anthropic.types import MessageParam as AnthropicMessageParam
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from .anthropic import ToolResultMessage
from .author import Author


class ToolResponseWrapper(BaseModel):
    author: Optional[Author] = None
    tool_messages: Optional[List[ToolMessageParam]] = None
    tool_result_message: Optional[Union[AnthropicMessageParam, ToolResultMessage]] = None
