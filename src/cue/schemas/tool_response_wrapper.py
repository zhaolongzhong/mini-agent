from typing import List, Union, Optional

from pydantic import BaseModel

from .author import Author


class AgentHandoffResult(BaseModel):
    from_agent_id: str
    to_agent_id: str
    context: Union[str, List]
    message: Optional[str] = None


class ToolResponseWrapper(BaseModel):
    author: Optional[Author] = None
    tool_messages: Optional[List[dict]] = None
    tool_result_message: Optional[dict] = None
    agent_handoff_result: Optional[AgentHandoffResult] = None
    base64_images: list = None
