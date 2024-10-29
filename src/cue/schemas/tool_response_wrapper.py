from typing import List, Optional, Union

from anthropic.types import MessageParam as AnthropicMessageParam
from anthropic.types.beta import BetaMessageParam
from openai.types.chat import ChatCompletionToolMessageParam as ToolMessageParam
from pydantic import BaseModel

from .author import Author


class AgentHandoffResult(BaseModel):
    from_agent_id: str
    to_agent_id: str
    context: Union[str, List]
    message: Optional[str] = None


class ToolResponseWrapper(BaseModel):
    author: Optional[Author] = None
    tool_messages: Optional[List[ToolMessageParam]] = None
    tool_result_message: Optional[Union[AnthropicMessageParam, BetaMessageParam]] = None
    agent_handoff_result: Optional[AgentHandoffResult] = None
    base64_images: list = None
