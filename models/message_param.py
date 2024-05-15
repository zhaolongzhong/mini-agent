from typing import Union

from models.message import Message
from models.tool_call import AssistantMessage, ToolMessage

ChatCompletionMessageParam = Union[
    Message,  # system, user
    AssistantMessage,  # assistant
    ToolMessage,  # tool
]

MessageLike = ChatCompletionMessageParam
