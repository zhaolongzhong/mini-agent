from typing import Union

from .message import Message
from .tool_call import AssistantMessage, ToolMessage

ChatCompletionMessageParam = Union[Message, AssistantMessage, ToolMessage]

MessageLike = ChatCompletionMessageParam
