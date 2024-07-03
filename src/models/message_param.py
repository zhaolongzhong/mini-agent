from models.message import Message
from models.tool_call import AssistantMessage, ToolMessage

ChatCompletionMessageParam = Message | AssistantMessage | ToolMessage

MessageLike = ChatCompletionMessageParam
