from typing import List, Optional, Union

from anthropic.types import MessageParam as AnthropicMessageParam
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from .anthropic import ToolResultMessage


class ToolResponseWrapper(BaseModel):
    tool_messages: Optional[List[ToolMessageParam]] = None
    tool_result_message: Optional[Union[AnthropicMessageParam, ToolResultMessage]] = None
