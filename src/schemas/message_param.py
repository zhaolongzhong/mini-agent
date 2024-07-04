from schemas.message import Message
from schemas.tool_call import AssistantMessage, ToolMessage

ChatCompletionMessageParam = Message | AssistantMessage | ToolMessage

MessageLike = ChatCompletionMessageParam
